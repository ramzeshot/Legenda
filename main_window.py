from __future__ import annotations
import os, csv, json
from pathlib import Path
from typing import List
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMenuBar, QMenu, QStatusBar,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QMessageBox, QFileDialog, QSystemTrayIcon, QStyle, QLineEdit, QComboBox,
    QTableView, QSizePolicy, QHeaderView
)
from PyQt6.QtGui import QAction, QIcon, QDesktopServices
from PyQt6.QtCore import Qt, QUrl

from license_manager import mode_label, device_limit
from device_dialog import DeviceDialog
from group_dialog import GroupDialog
from report_dialog import ReportDialog
from ping_worker import PingWorker, DeviceJob
from data_model import Device
from storage import save_project_json, load_project_json
from translations import tr, set_language
from themes import apply_theme
from activate_dialog import ActivateDialog
from audio import AudioAlert
from history import ensure_log, log_status_change
from history_chart import HistoryChart
from tables import DeviceTableModel, DeviceFilterProxy, ProgressDelegate
from scan_dialog import ScanDialog, ScanItem
from app_lists import DEFAULT_GROUPS, DEFAULT_DIVISIONS
from utils_paths import resource_path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        try: set_language("uz")
        except Exception: pass

        self.setWindowTitle("IP Monitoring 2025")
        # Window icon (reliable path)
        icon_path = resource_path("resources", "app.ico")
        if not os.path.exists(icon_path):
            icon_path = resource_path("resources", "app.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(1160, 780)

        # Data
        self.devices: List[Device] = []
        self.groups: List[str] = []
        self._load_groups()
        self.worker: PingWorker | None = None
        self._offline_alerted: set[int] = set()

        # Logs
        self.logs_dir = Path("logs"); self.log_path = str(self.logs_dir / "events.csv"); ensure_log(self.log_path)

        # Audio
        self.alert = AudioAlert(resource_path("resources", "alert.wav"))

        # UI
        self._build_menus()
        self._build_central_ui()

        # Model
        self.model = DeviceTableModel(self.devices)
        self.proxy = DeviceFilterProxy()
        self.proxy.setSourceModel(self.model)
        self.view.setModel(self.proxy)
        self.view.setItemDelegateForColumn(6, ProgressDelegate())
        self.view.setSortingEnabled(True)
        self.view.setAlternatingRowColors(True)

        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stat.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self._connect_signals()
        self._retranslate_ui()
        self._build_tray()

        # Example rows (can remove)
        self._append_device(Device("9202","1-ChQV","Kamera","92.2.1.1",30,False,True,10))
        self._append_device(Device("9203","5-ChQV","IP PBX","92.3.5.1",30,True,False,17))
        self._append_device(Device("9262","Dout-ota","Kamera","92.62.1.1",30,True,False,18))
        self.populate_group_filter(); self.recompute_stats(); self.apply_filter()

    # groups.json
    def _load_groups(self):
        try:
            with open("groups.json","r",encoding="utf-8") as f:
                data = json.load(f)
            loaded = data.get("groups", [])
            base = set(DEFAULT_GROUPS)
            self.groups = sorted(base | set(loaded))
        except Exception:
            self.groups = DEFAULT_GROUPS.copy()

    def _save_groups(self):
        try:
            with open("groups.json","w",encoding="utf-8") as f:
                json.dump({"groups": sorted(set(self.groups))}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # UI
    def _build_menus(self):
        menubar = QMenuBar(self)
        self.menu_file = QMenu(self); self.menu_menu = QMenu(self); self.menu_help = QMenu(self)
        menubar.addMenu(self.menu_file); menubar.addMenu(self.menu_menu); menubar.addMenu(self.menu_help); self.setMenuBar(menubar)

        self.act_save = QAction(self); self.act_load = QAction(self); self.act_report = QAction(self)
        self.act_export_csv = QAction("Joriy holatni CSV saqlash…", self)
        self.act_open_logs = QAction("Log papkasini ochish", self)
        self.act_chart = QAction("Tarix grafikasi (24h)", self)
        self.menu_file.addAction(self.act_save); self.menu_file.addAction(self.act_load); self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_report); self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_export_csv); self.menu_file.addAction(self.act_open_logs); self.menu_file.addAction(self.act_chart)

        self.act_add_group = QAction(self); self.menu_menu.addAction(self.act_add_group)
        self.menu_theme = self.menu_menu.addMenu(""); self.act_theme_win = QAction(self); self.act_theme_dark = QAction(self); self.act_theme_light = QAction(self)
        self.menu_theme.addAction(self.act_theme_win); self.menu_theme.addAction(self.act_theme_dark); self.menu_theme.addAction(self.act_theme_light)
        self.menu_lang = self.menu_menu.addMenu(""); self.act_lang_uz = QAction(self); self.act_lang_ru = QAction(self); self.act_lang_en = QAction(self)
        self.menu_lang.addAction(self.act_lang_uz); self.menu_lang.addAction(self.act_lang_ru); self.menu_lang.addAction(self.act_lang_en)

        self.act_activate = QAction(self); self.act_update = QAction(self); self.act_about = QAction(self); self.act_support = QAction(self)
        self.menu_help.addAction(self.act_activate); self.menu_help.addAction(self.act_update); self.menu_help.addAction(self.act_about); self.menu_help.addAction(self.act_support)

        self.sb = QStatusBar(); self.setStatusBar(self.sb); self._update_status()

    def _build_central_ui(self):
        central = QWidget(); self.setCentralWidget(central); root = QVBoxLayout(central)
        # Top filter
        filt = QHBoxLayout()
        self.ed_search = QLineEdit(); self.ed_search.setPlaceholderText("Qidirish (nom yoki IP)…")
        self.cb_group = QComboBox(); self.cb_status = QComboBox(); self.cb_status.addItems(["Barchasi","Online","Offline"])
        self.btn_clear_filter = QPushButton("Filtrni tozalash")
        filt.addWidget(QLabel("Qidiruv:")); filt.addWidget(self.ed_search,2)
        filt.addWidget(QLabel("Guruh:")); filt.addWidget(self.cb_group,1)
        filt.addWidget(QLabel("Holat:")); filt.addWidget(self.cb_status,1)
        filt.addWidget(self.btn_clear_filter); root.addLayout(filt)

        self.view = QTableView(); root.addWidget(self.view,1)

        bottom = QHBoxLayout()
        stat_box = QVBoxLayout(); self.lbl_stat_title = QLabel("Guruh | Jami | Online | Offline"); stat_box.addWidget(self.lbl_stat_title)
        self.stat = QTableWidget(0,4); self.stat.setHorizontalHeaderLabels(["Guruh","Jami","Online","Offline"]); stat_box.addWidget(self.stat)
        bottom.addLayout(stat_box)

        btns = QVBoxLayout()
        self.btn_add = QPushButton(tr("add_device"))
        self.btn_edit = QPushButton("Tahrirlash")
        self.btn_del = QPushButton(tr("delete_device"))
        self.btn_start_stop = QPushButton(tr("start_monitor"))
        self.btn_report = QPushButton(tr("report"))
        self.btn_scan = QPushButton("Skanerlash")
        for w in (self.btn_add,self.btn_edit,self.btn_del,self.btn_start_stop,self.btn_report,self.btn_scan): 
            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding); btns.addWidget(w,1)
        bottom.addLayout(btns); root.addLayout(bottom)

    def _connect_signals(self):
        self.act_save.triggered.connect(self.action_save); self.act_load.triggered.connect(self.action_load)
        self.act_report.triggered.connect(self.action_report); self.act_export_csv.triggered.connect(self.export_current_csv)
        self.act_open_logs.triggered.connect(self.open_logs_dir); self.act_chart.triggered.connect(self.show_history_chart)
        self.act_add_group.triggered.connect(self.add_group)
        self.act_theme_win.triggered.connect(lambda: apply_theme("windows"))
        self.act_theme_dark.triggered.connect(lambda: apply_theme("dark"))
        self.act_theme_light.triggered.connect(lambda: apply_theme("light"))
        self.act_lang_uz.triggered.connect(lambda: self.change_lang("uz"))
        self.act_lang_ru.triggered.connect(lambda: self.change_lang("ru"))
        self.act_lang_en.triggered.connect(lambda: self.change_lang("en"))
        self.act_activate.triggered.connect(self.reactivate); self.act_update.triggered.connect(self.fake_update)
        self.act_about.triggered.connect(self.show_about); self.act_support.triggered.connect(self.show_support)

        self.btn_add.clicked.connect(self.add_device); self.btn_edit.clicked.connect(self.edit_device); self.btn_del.clicked.connect(self.delete_selected)
        self.btn_start_stop.clicked.connect(self.toggle_monitoring); self.btn_report.clicked.connect(self.action_report); self.btn_scan.clicked.connect(self.open_scan)
        self.ed_search.textChanged.connect(self.apply_filter); self.cb_group.currentIndexChanged.connect(self.apply_filter); self.cb_status.currentIndexChanged.connect(self.apply_filter); self.btn_clear_filter.clicked.connect(self.clear_filter)

    def _retranslate_ui(self):
        self.menu_file.setTitle(tr("file")); self.menu_menu.setTitle(tr("menu")); self.menu_help.setTitle(tr("help"))
        self.act_save.setText(tr("save_project")); self.act_load.setText(tr("load_project")); self.act_report.setText(tr("report_menu"))
        self.act_add_group.setText(tr("add_group")); self.menu_theme.setTitle(tr("theme")); self.act_theme_win.setText(tr("theme_win")); self.act_theme_dark.setText(tr("theme_dark")); self.act_theme_light.setText(tr("theme_light"))
        self.menu_lang.setTitle(tr("lang")); self.act_lang_uz.setText(tr("lang_uz")); self.act_lang_ru.setText(tr("lang_ru")); self.act_lang_en.setText(tr("lang_en"))
        self.act_activate.setText(tr("activate")); self.act_update.setText(tr("update")); self.act_about.setText(tr("about")); self.act_support.setText("Mutaxassisga murojaat")
        self.stat.setHorizontalHeaderLabels(["Guruh","Jami","Online","Offline"]); self.lbl_stat_title.setText("Guruh | Jami | Online | Offline")
        self.btn_add.setText(tr("add_device")); self.btn_del.setText(tr("delete_device")); self.btn_report.setText(tr("report"))
        self.btn_start_stop.setText(tr("stop_monitor") if (self.worker and self.worker.isRunning()) else tr("start_monitor"))
        self._update_status()

    # tray
    def _build_tray(self):
        icon_path = resource_path("resources", "app.ico")
        if not os.path.exists(icon_path): icon_path = resource_path("resources", "app.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray = QSystemTrayIcon(icon, self); self.tray.setIcon(icon)
        menu = QMenu(); act_show = QAction("Oynani ko‘rsatish", self); act_toggle = QAction("Start/Stop monitoring", self); act_exit = QAction("Chiqish", self)
        act_show.triggered.connect(self._tray_show); act_toggle.triggered.connect(self.toggle_monitoring); act_exit.triggered.connect(self._tray_exit)
        menu.addAction(act_show); menu.addAction(act_toggle); menu.addSeparator(); menu.addAction(act_exit)
        self.tray.setContextMenu(menu); self.tray.activated.connect(self._tray_activated); self.tray.show()

    def _tray_show(self): self.showNormal(); self.activateWindow(); self.raise_()
    def _tray_exit(self):
        try:
            if self.worker and self.worker.isRunning(): self.worker.stop(); self.worker.wait(1500)
        finally:
            self.tray.hide(); self.close()
    def _tray_activated(self, reason): 
        if reason == QSystemTrayIcon.ActivationReason.Trigger: self._tray_show()

    # help/menu callbacks
    def change_lang(self, lang: str):
        set_language(lang); self._retranslate_ui(); QMessageBox.information(self, "Info", f"Til o‘zgartirildi: {lang}")
    def reactivate(self): ActivateDialog(self).exec(); self._update_status()
    def fake_update(self): QMessageBox.information(self, tr("update"), "Yangilash xizmati keyingi relizda qo‘shiladi.")
    def show_about(self): QMessageBox.information(self, tr("about"), "IP Monitoring 2025\n" + f"Holat: {mode_label()}")
    def show_support(self): QMessageBox.information(self, "Mutaxassisga murojaat", "Telefon: +998 77 047 28-31\nEmail: vapoevramz1@gmail.com")

    def _update_status(self): self.sb.showMessage(f"IP MONITORING 2025 – {mode_label()}")

    def _append_device(self, d: Device):
        self.model.add_device(d)
        if d.group not in self.groups: self.groups.append(d.group); self._save_groups()

    def _refresh_row_from_device(self, row: int): self.model.update_row(row)

    def get_all_jobs(self) -> List[DeviceJob]:
        return [DeviceJob(row=i, ip=d.ip, interval=max(1, d.interval)) for i,d in enumerate(self.devices)]

    def recompute_stats(self):
        stats = {}
        for d in self.devices:
            g=d.group; stats.setdefault(g,[0,0,0]); stats[g][0]+=1; stats[g][1]+=1 if d.online else 0; stats[g][2]+=0 if d.online else 1
        self.stat.setRowCount(0)
        for g,(jami,onl,off) in sorted(stats.items()):
            rr=self.stat.rowCount(); self.stat.insertRow(rr)
            self.stat.setItem(rr,0,QTableWidgetItem(g)); self.stat.setItem(rr,1,QTableWidgetItem(str(jami)))
            self.stat.setItem(rr,2,QTableWidgetItem(str(onl))); self.stat.setItem(rr,3,QTableWidgetItem(str(off)))

    def populate_group_filter(self):
        groups = sorted(set(DEFAULT_GROUPS) | {d.group for d in self.devices} | set(self.groups))
        self.cb_group.blockSignals(True); self.cb_group.clear(); self.cb_group.addItem("Barchasi"); [self.cb_group.addItem(g) for g in groups]; self.cb_group.blockSignals(False)

    # filter
    def clear_filter(self): self.ed_search.clear(); self.cb_group.setCurrentIndex(0); self.cb_status.setCurrentIndex(0); self.apply_filter()
    def apply_filter(self):
        term=self.ed_search.text(); grp=self.cb_group.currentText(); st=self.cb_status.currentText(); self.proxy.setFilters(term, grp, st)

    # dialogs/actions
    def show_history_chart(self): HistoryChart(self.log_path, self).exec()

    def add_group(self):
        dlg = GroupDialog(self.groups, self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self.groups = dlg.get_groups(); self._save_groups(); self.populate_group_filter(); self.apply_filter()

    def add_device(self):
        lim = device_limit()
        if lim is not None and len(self.devices) >= lim:
            QMessageBox.information(self, "Cheklov", f"DEMO rejimida maksimal {lim} ta qurilma qo‘shishingiz mumkin."); return
        dlg = DeviceDialog(self.groups, self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            d = dlg.get_data()
            dev = Device(d["group"], d["division"], d["name"], d["ip"], int(d["interval"]), bool(d["alert"]), False, 0)
            self._append_device(dev); self.populate_group_filter(); self.recompute_stats(); self.apply_filter()
            if self.worker and self.worker.isRunning(): self.worker.set_jobs(self.get_all_jobs())

    def edit_device(self):
        idx = self.view.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Tanlov", "Tahrirlash uchun qatorni tanlang."); return
        source_row = self.proxy.mapToSource(idx).row()
        if not (0 <= source_row < len(self.devices)): return
        dev = self.devices[source_row]
        dlg = DeviceDialog(self.groups, self, device_data=dev.__dict__)
        if dlg.exec() == dlg.DialogCode.Accepted:
            d = dlg.get_data()
            dev.group=d["group"]; dev.division=d["division"]; dev.name=d["name"]; dev.ip=d["ip"]; dev.interval=int(d["interval"]); dev.alert=bool(d["alert"])
            self.model.update_row(source_row); self.populate_group_filter(); self.recompute_stats()
            if self.worker and self.worker.isRunning(): self.worker.set_jobs(self.get_all_jobs())

    def delete_selected(self):
        idx = self.view.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Tanlov", "O‘chirish uchun bir qatorni tanlang."); return
        source_row = self.proxy.mapToSource(idx).row()
        if not (0 <= source_row < len(self.devices)): return
        self.model.remove_row(source_row); self.populate_group_filter(); self.recompute_stats()
        if self.worker and self.worker.isRunning(): self.worker.set_jobs(self.get_all_jobs())

    # file menu
    def action_save(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("save_project"), "project.json", "JSON (*.json)")
        if path:
            try: save_project_json(path, self.devices); QMessageBox.information(self, "OK", "Loyiha saqlandi.")
            except Exception as e: QMessageBox.critical(self, "Xatolik", f"Saqlashda xatolik: {e}")

    def action_load(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("load_project"), "", "JSON (*.json)")
        if path:
            try:
                if self.worker and self.worker.isRunning(): self.worker.stop(); self.worker.wait(2000); self.btn_start_stop.setText(tr("start_monitor"))
                devs = load_project_json(path); self.devices.clear(); self.model.beginResetModel(); self.devices.extend(devs); self.model.endResetModel()
                self.populate_group_filter(); self.recompute_stats(); self.apply_filter()
            except Exception as e:
                QMessageBox.critical(self, "Xatolik", f"Yuklashda xatolik: {e}")

    def action_report(self):
        if not self.devices: QMessageBox.information(self, "Ma’lumot yo‘q", "Hisobot uchun qurilmalar yo‘q.")
        else: ReportDialog(self.devices, self).exec()

    def export_current_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "CSV saqlash", "ip_current.csv", "CSV (*.csv)")
        if not path: return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f); w.writerow(["Guruh","Bo‘linma","Qurilma","IP","Holat","Ping(ms)"])
                for r in range(self.proxy.rowCount()):
                    i = self.proxy.index(r,0); srow = self.proxy.mapToSource(i).row(); d = self.devices[srow]
                    w.writerow([d.group, d.division, d.name, d.ip, "Online" if d.online else "Offline", d.last_ms if d.online else ""])
            QMessageBox.information(self, "OK", "CSV saqlandi.")
        except Exception as e:
            QMessageBox.critical(self, "Xatolik", f"CSV saqlashda xatolik: {e}")

    def open_logs_dir(self):
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            url = QUrl.fromLocalFile(str(self.logs_dir.resolve())); QDesktopServices.openUrl(url)
        except Exception as e:
            QMessageBox.critical(self, "Xatolik", f"Log papkasini ochishda xatolik: {e}")

    # monitoring
    def toggle_monitoring(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop(); self.worker.wait(2000); self.btn_start_stop.setText(tr("start_monitor")); self._update_status(); return
        if not self.devices:
            QMessageBox.information(self, "Ma’lumot yo‘q", "Monitoring uchun kamida bitta qurilma qo‘shing."); return
        self.worker = PingWorker(parent=self); self.worker.ping_result.connect(self.on_ping_result)
        if hasattr(self.worker, "started_monitoring"): self.worker.started_monitoring.connect(lambda: self.sb.showMessage("Monitoring boshlandi…"))
        if hasattr(self.worker, "stopped_monitoring"): self.worker.stopped_monitoring.connect(lambda: self.sb.showMessage(f"Monitoring to‘xtadi – {mode_label()}"))
        self.worker.set_jobs(self.get_all_jobs()); self.worker.start(); self.btn_start_stop.setText(tr("stop_monitor"))

    def on_ping_result(self, row: int, online: bool, ms: int):
        if not (0 <= row < len(self.devices)): return
        d = self.devices[row]; was_online = d.online; d.online = online; d.last_ms = ms if online else d.last_ms
        self._refresh_row_from_device(row); self.recompute_stats()
        if was_online != online:
            log_status_change(self.log_path, d.group, d.division, d.name, d.ip, online, ms)
            title = f"{d.name} [{d.ip}]"
            if self.tray.isVisible():
                try:
                    if online: self.tray.showMessage(title, "Online bo‘ldi", QSystemTrayIcon.MessageIcon.Information, 3500)
                    else: self.tray.showMessage(title, "OFFLINE bo‘ldi!", QSystemTrayIcon.MessageIcon.Warning, 3500)
                except Exception: pass
            if was_online and (not online):
                try: self.alert.play()
                except Exception: pass

    # close behavior
    def closeEvent(self, event):
        tray = getattr(self, "tray", None)
        if tray is not None and tray.isVisible():
            self.hide()
            try:
                tray.showMessage("IP Monitoring 2025", "Dastur trayda ishlashda davom etadi.", QSystemTrayIcon.MessageIcon.Information, 2500)
            except Exception: pass
            event.ignore(); return
        super().closeEvent(event)

    # scanning
    def open_scan(self):
        existing = {d.ip for d in self.devices}; groups = self.groups[:] if self.groups else DEFAULT_GROUPS; divisions = DEFAULT_DIVISIONS
        dlg = ScanDialog(existing_ips=existing, groups=groups, divisions=divisions, parent=self)
        def on_ready(items: list):
            for it in items:
                dev = Device(group=it.group or (groups[0] if groups else "Default"), division=it.division or "", name=(it.name or f"Device {it.ip}"),
                             ip=it.ip, interval=int(it.interval), alert=False, online=bool(it.online), last_ms=int(it.ms))
                self._append_device(dev)
            self.populate_group_filter(); self.recompute_stats()
            if self.worker and self.worker.isRunning(): self.worker.set_jobs(self.get_all_jobs())
        dlg.devices_ready.connect(on_ready); dlg.exec()


# === Addons: non-invasive helpers for IP Monitor integration ===
try:
    from integration_hooks import _get_qtable  # reuse table finder
except Exception:
    _get_qtable = None

def _addons_all_ips_set(self):
    tbl = _get_qtable(self) if _get_qtable else None
    ips = set()
    if tbl:
        # try find IP column by header
        headers = [tbl.horizontalHeaderItem(c).text().lower() if tbl.horizontalHeaderItem(c) else "" for c in range(tbl.columnCount())]
        try:
            c_ip = next(i for i,h in enumerate(headers) if h.strip() in ["ip","ip address","ip manzil"] or "ip" == h.strip())
        except StopIteration:
            c_ip = None
        for r in range(tbl.rowCount()):
            if c_ip is not None:
                it = tbl.item(r, c_ip)
                if it and it.text().strip():
                    ips.add(it.text().strip())
    return ips

def _addons_add_single_device(self, data: dict):
    tbl = _get_qtable(self) if _get_qtable else None
    if not tbl:
        return
    # map headers
    headers = [tbl.horizontalHeaderItem(c).text().lower() if tbl.horizontalHeaderItem(c) else "" for c in range(tbl.columnCount())]
    idx = {
        "group": next((i for i,h in enumerate(headers) if h.startswith("guruh") or h.startswith("group")), None),
        "division": next((i for i,h in enumerate(headers) if h.startswith("bo") or h.startswith("division")), None),
        "name": next((i for i,h in enumerate(headers) if "nom" in h or "name" in h), None),
        "ip": next((i for i,h in enumerate(headers) if h.strip() in ["ip","ip address","ip manzil"]), None),
        "status": next((i for i,h in enumerate(headers) if "holat" in h or "status" in h), None),
        "ping": next((i for i,h in enumerate(headers) if "ping" in h), None),
        "progress": next((i for i,h in enumerate(headers) if "progress" in h), None),
    }
    # don't add duplicates
    if data.get("ip") and data["ip"] in _addons_all_ips_set(self):
        return
    r = tbl.rowCount(); tbl.insertRow(r)
    from PyQt6.QtWidgets import QTableWidgetItem
    def setc(i, val):
        if i is None: return
        try:
            tbl.setItem(r, i, QTableWidgetItem(str(val)))
        except Exception:
            pass
    setc(idx["group"], data.get("group",""))
    setc(idx["division"], data.get("division",""))
    setc(idx["name"], data.get("name",""))
    setc(idx["ip"], data.get("ip",""))
    setc(idx["status"], "Offline")
    setc(idx["ping"], "")
    # progress will be set by integration timer later

def _addons_add_devices_from_scan(self, devs: list):
    for d in devs:
        _addons_add_single_device(self, d)

def _addons_open_device_dialog(self, preset_ip=None):
    try:
        from addons.ui.device_dialog import DeviceDialog
    except Exception:
        return
    groups = getattr(self, "groups", []) or []
    divisions = getattr(self, "divisions", []) or []
    existing = _addons_all_ips_set(self)
    dlg = DeviceDialog(self, groups=groups, divisions=divisions, existing_ips=existing, preset_ip=preset_ip)
    if dlg.exec():
        data = dlg.result_data()
        _addons_add_single_device(self, data)

def _addons_retranslate_ui(self):
    # Placeholder: if your UI supports live retranslation, update labels here.
    # Kept empty to avoid breaking user code.
    pass

# Try to bind helpers to MainWindow
try:
    # Find MainWindow symbol
    _MainWindow = None
    for _name, _obj in globals().items():
        try:
            from PyQt6.QtWidgets import QMainWindow as _QMW
            if isinstance(_obj, type) and issubclass(_obj, _QMW) and _name.lower() == "mainwindow":
                _MainWindow = _obj
                break
        except Exception:
            pass
    if _MainWindow is not None:
        _MainWindow.all_ips_set = _addons_all_ips_set
        _MainWindow.add_single_device = _addons_add_single_device
        _MainWindow.add_devices_from_scan = _addons_add_devices_from_scan
        _MainWindow.open_device_dialog = _addons_open_device_dialog
        _MainWindow.retranslate_ui = _addons_retranslate_ui
except Exception:
    pass

# === End Addons helpers ===
