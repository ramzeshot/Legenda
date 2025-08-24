from __future__ import annotations
import ipaddress, subprocess, sys, re
from dataclasses import dataclass
from typing import List, Set, Optional
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QCheckBox, QComboBox)
from ping_worker import ping_once
from app_lists import DEFAULT_GROUPS, DEFAULT_DIVISIONS

@dataclass
class ScanItem:
    ip: str
    interval: int
    mac: str
    online: bool
    ms: int
    exists: bool = False
    group: str = ''
    division: str = ''
    name: str = ''

def _get_mac(ip: str) -> str:
    try:
        if sys.platform.startswith("win"):
            out = subprocess.run(["arp","-a", ip], capture_output=True, text=True, encoding="mbcs", errors="ignore", timeout=2)
            m = re.search(r"([0-9a-fA-F]{2}(?:-[0-9a-fA-F]{2}){5})", out.stdout or "")
            return m.group(1).lower() if m else ""
        else:
            out = subprocess.run(["arp","-n", ip], capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=2)
            m = re.search(r"([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})", out.stdout or "")
            return m.group(1).lower() if m else ""
    except Exception:
        return ""

def _ip_range(start_ip: str, end_ip: str) -> List[str]:
    s = ipaddress.ip_address(start_ip); e = ipaddress.ip_address(end_ip)
    if int(e) < int(s): s, e = e, s
    return [str(ipaddress.ip_address(v)) for v in range(int(s), int(e)+1)]

class ScanWorker(QThread):
    progress = pyqtSignal(int, int)
    scanned = pyqtSignal(int, object)
    finished_scan = pyqtSignal(int, int, int)
    def __init__(self, ips: List[str], interval: int, existing_ips: Set[str], parent: Optional[QObject] = None):
        super().__init__(parent); self.ips = ips; self.interval = interval; self.existing = existing_ips; self._running = False
    def stop(self): self._running = False
    def run(self):
        total=len(self.ips); done=0; on_count=0; exist_count=0; self._running=True
        for i, ip in enumerate(self.ips):
            if not self._running: break
            online, ms = ping_once(ip, timeout_ms=1000)
            mac = _get_mac(ip) if online else ""
            exists = ip in self.existing
            if online: on_count += 1
            if exists: exist_count += 1
            item = ScanItem(ip=ip, interval=self.interval, mac=mac, online=online, ms=ms, exists=exists)
            self.scanned.emit(i, item); done += 1; self.progress.emit(done, total); self.msleep(10)
        self.finished_scan.emit(total, on_count, exist_count)

class ScanDialog(QDialog):
    devices_ready = pyqtSignal(list)
    device_added = pyqtSignal(dict)
    def __init__(self, existing_ips: Optional[Set[str]] = None, groups: Optional[List[str]] = None,
                 divisions: Optional[List[str]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("IP diapazonini skanerlash"); self.resize(900,560)
        self.existing_ips = existing_ips or set(); self._worker: Optional[ScanWorker] = None; self._results: List[ScanItem] = []
        self._groups = groups or DEFAULT_GROUPS; self._divisions = divisions or DEFAULT_DIVISIONS

        root = QVBoxLayout(self)
        top = QHBoxLayout(); root.addLayout(top)
        top.addWidget(QLabel("Boshlang‘ich IP:")); self.ed_start = QLineEdit(self); self.ed_start.setPlaceholderText("192.168.1.1"); top.addWidget(self.ed_start,1)
        top.addWidget(QLabel("Tugash IP:")); self.ed_end = QLineEdit(self); self.ed_end.setPlaceholderText("192.168.1.254"); top.addWidget(self.ed_end,1)
        top.addWidget(QLabel("Interval (s):")); self.sb_interval=QSpinBox(self); self.sb_interval.setRange(1,3600); self.sb_interval.setValue(30); top.addWidget(self.sb_interval)
        self.btn_start=QPushButton("Skanerlash"); self.btn_stop=QPushButton("To‘xtatish"); self.btn_stop.setEnabled(False); top.addWidget(self.btn_start); top.addWidget(self.btn_stop)

        gp = QHBoxLayout(); root.addLayout(gp)
        gp.addWidget(QLabel("Guruh:")); self.cb_group=QComboBox(); self.cb_group.addItems(self._groups); gp.addWidget(self.cb_group)
        gp.addWidget(QLabel("Bo‘linma:")); self.cb_division=QComboBox(); self.cb_division.addItems(self._divisions); gp.addWidget(self.cb_division)

        self.tbl = QTableWidget(0,6, self); self.tbl.setHorizontalHeaderLabels(["t/r","IP","Interval","MAC","Holati","Ping (ms)"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c in (2,3,4,5): self.tbl.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.setSelectionBehavior(self.tbl.SelectionBehavior.SelectRows); self.tbl.setSelectionMode(self.tbl.SelectionMode.ExtendedSelection)
        root.addWidget(self.tbl,1)

        bottom=QHBoxLayout(); root.addLayout(bottom)
        self.chk_skip_existing = QCheckBox("Mavjud IP’larni o‘tkazib yuborish"); self.chk_skip_existing.setChecked(True); bottom.addWidget(self.chk_skip_existing); bottom.addStretch(1)
        self.btn_add_one=QPushButton("Bittalab qo‘shish"); self.btn_add_selected=QPushButton("Tanlanganlarni qo‘shish"); self.btn_add_all=QPushButton("Barchasini qo‘shish"); self.btn_cancel=QPushButton("Yopish")
        for b in (self.btn_add_one,self.btn_add_selected,self.btn_add_all,self.btn_cancel): bottom.addWidget(b)

        self.lbl_info=QLabel("Tayyor."); root.addWidget(self.lbl_info)

        self.btn_start.clicked.connect(self._start_scan); self.btn_stop.clicked.connect(self._stop_scan)
        self.btn_add_selected.clicked.connect(self._do_add_selected); self.btn_add_all.clicked.connect(self._do_add_all); self.btn_add_one.clicked.connect(self._do_add_one); self.btn_cancel.clicked.connect(self.reject)

    def _start_scan(self):
        start_ip=self.ed_start.text().strip(); end_ip=self.ed_end.text().strip()
        if not start_ip or not end_ip: QMessageBox.warning(self, "Xatolik", "Boshlang‘ich va tugash IP’larni kiriting."); return
        try: ips=_ip_range(start_ip, end_ip)
        except Exception: QMessageBox.critical(self, "Xatolik", "IP diapazon noto‘g‘ri."); return
        if len(ips)>4096:
            ret=QMessageBox.question(self,"Ogohlantirish",f"{len(ips)} ta IP skan qilinadi. Davom etamizmi?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
            if ret!=QMessageBox.StandardButton.Yes: return
        self.tbl.setRowCount(0); self._results=[]; interval=int(self.sb_interval.value())
        self._worker=ScanWorker(ips=ips, interval=interval, existing_ips=self.existing_ips, parent=self)
        self._worker.progress.connect(self._on_progress); self._worker.scanned.connect(self._on_scanned); self._worker.finished_scan.connect(self._on_finished)
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True); self.lbl_info.setText("Skanerlash boshlandi…"); self._worker.start()

    def _stop_scan(self):
        if self._worker and self._worker.isRunning(): self._worker.stop()
        self.btn_stop.setEnabled(False); self.btn_start.setEnabled(True)

    def _on_progress(self, done: int, total: int):
        self.lbl_info.setText(f"Skanerlash: {done}/{total} …")

    def _on_scanned(self, index: int, item: ScanItem):
        if self.chk_skip_existing.isChecked() and item.exists:
            self._results.append(item); return
        self._results.append(item); r=self.tbl.rowCount(); self.tbl.insertRow(r); self.tbl.setItem(r,0,QTableWidgetItem(str(r+1)))
        ip_it=QTableWidgetItem(item.ip); self.tbl.setItem(r,1,ip_it)
        self.tbl.setItem(r,2,QTableWidgetItem(str(item.interval))); self.tbl.setItem(r,3,QTableWidgetItem(item.mac or ""))
        st_it=QTableWidgetItem("Online" if item.online else "Offline"); self.tbl.setItem(r,4,st_it)
        self.tbl.setItem(r,5,QTableWidgetItem(str(item.ms if item.online else "")))

    def _on_finished(self,total:int,on_count:int,exist_count:int):
        self.btn_stop.setEnabled(False); self.btn_start.setEnabled(True)
        self.lbl_info.setText(f"Jami {total} ta IP skanerlandi, {on_count} ta Online. {exist_count} tasi ro‘yxatda mavjud.")

    def _filtered_results_for_add(self, only_selected: bool) -> List[ScanItem]:
        res: List[ScanItem] = []; sel_group=self.cb_group.currentText(); sel_div=self.cb_division.currentText()
        if only_selected:
            rows={i.row() for i in self.tbl.selectedIndexes()}; to_iter=[(r,self._results[r]) for r in sorted(rows) if 0 <= r < len(self._results)]
        else:
            to_iter=list(enumerate(self._results))
        for r,it in to_iter:
            if self.chk_skip_existing.isChecked() and it.exists: continue
            it.group=sel_group; it.division=sel_div; 
            if not getattr(it,'name',''): it.name=''
            res.append(it)
        return res

    def _do_add_selected(self):
        if self._worker and self._worker.isRunning(): QMessageBox.information(self, "Ma’lumot", "Iltimos, skanerlash tugashini kuting yoki to‘xtating."); return
        devices=self._filtered_results_for_add(True)
        if not devices: QMessageBox.information(self,"Ma’lumot","Tanlangan qurilmalar yo‘q (yoki barchasi mavjud)."); return
        self.devices_ready.emit(devices)

    def _do_add_all(self):
        if self._worker and self._worker.isRunning(): QMessageBox.information(self, "Ma’lumot", "Iltimos, skanerlash tugashini kuting yoki to‘xtating."); return
        devices=self._filtered_results_for_add(False)
        if not devices: QMessageBox.information(self,"Ma’lumot","Qo‘shiladigan qurilmalar yo‘q (yoki barchasi mavjud)."); return
        self.devices_ready.emit(devices)

    def _do_add_one(self):
        if self._worker and self._worker.isRunning(): QMessageBox.information(self, "Ma’lumot", "Iltimos, skanerlash tugashini kuting yoki to‘xtating."); return
        rows=sorted({i.row() for i in self.tbl.selectedIndexes()})
        if not rows: QMessageBox.information(self,"Ma’lumot","Avval bitta qatorni tanlang."); return
        r=rows[0]
        if not (0 <= r < len(self._results)): return
        it=self._results[r]
        if it.exists and self.chk_skip_existing.isChecked(): QMessageBox.information(self,"Ma’lumot","Ushbu IP allaqachon ro‘yxatda bor."); return
        # Bitta qurilmani qo‘shish — sodda: bevosita dictionary
        dev = {"group": self.cb_group.currentText(), "division": self.cb_division.currentText(), "name": f"Device {it.ip}",
               "ip": it.ip, "interval": int(it.interval), "alert": False, "online": bool(it.online), "last_ms": int(it.ms)}
        self.device_added.emit(dev)
