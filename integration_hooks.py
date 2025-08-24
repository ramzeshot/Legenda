
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QApplication
from PyQt6.QtCore import QTimer
from addons.ui.report_dialog import ReportDialog
from addons.ui.history_dialog import HistoryDialog
from addons.ui.group_manager_dialog import GroupManagerDialog
from addons.ui.activation_dialog import ActivationDialog
from addons.ui.about_dialog import AboutDialog
from addons.ui.scan_dialog import ScanDialog
from addons.ui.device_dialog import DeviceDialog
from addons.widgets.table_helpers import set_status_cell, set_ping_cell, set_progress_value
from addons.services.theme import set_theme_and_apply
from addons.services.language import set_language
from addons.services.updater import check_updates

def _get_qtable(widget):
    for name in ["table", "tbl", "tableWidget", "devicesTable", "tblDevices"]:
        t = getattr(widget, name, None)
        if t is not None:
            return t
    try:
        from PyQt6.QtWidgets import QTableWidget
        tables = widget.findChildren(QTableWidget)
        if tables:
            return tables[0]
    except Exception:
        pass
    return None

def _collect_rows(window):
    tbl = _get_qtable(window)
    rows = []
    if not tbl:
        return rows
    cols = tbl.columnCount()
    headers = [tbl.horizontalHeaderItem(c).text() if tbl.horizontalHeaderItem(c) else "" for c in range(cols)]
    idx = {
        "group": next((i for i,h in enumerate(headers) if h.lower().startswith("guruh") or h.lower().startswith("group")), None),
        "division": next((i for i,h in enumerate(headers) if h.lower().startswith("bo") or h.lower().startswith("division")), None),
        "name": next((i for i,h in enumerate(headers) if "nom" in h.lower() or "name" in h.lower()), None),
        "ip": next((i for i,h in enumerate(headers) if h.strip().lower() in ["ip","ip address","ip manzil"]), None),
        "status": next((i for i,h in enumerate(headers) if "holat" in h.lower() or "status" in h.lower()), None),
        "ping": next((i for i,h in enumerate(headers) if "ping" in h.lower()), None),
        "progress": next((i for i,h in enumerate(headers) if "progress" in h.lower()), None),
    }
    for r in range(tbl.rowCount()):
        def cell(i):
            if i is None: return ""
            it = tbl.item(r,i)
            return it.text() if it else ""
        rows.append({
            "group": cell(idx["group"]),
            "division": cell(idx["division"]),
            "name": cell(idx["name"]),
            "ip": cell(idx["ip"]),
            "online": (cell(idx["status"]).strip().lower()=="online"),
            "ping_ms": float(cell(idx["ping"])) if cell(idx["ping"]).strip().replace('.','',1).isdigit() else None,
            "row": r,
            "col_status": idx["status"],
            "col_ping": idx["ping"],
            "col_progress": idx["progress"],
        })
    return rows

def _provider_from_table(window):
    rows = _collect_rows(window)
    stats = {}
    for d in rows:
        key = (d.get("group",""), d.get("division",""))
        s = stats.setdefault(key, {"group": key[0], "division": key[1], "total":0, "online":0, "offline":0})
        s["total"] += 1
        if d.get("online"): s["online"] += 1
        else: s["offline"] += 1
    return list(stats.values())

def _menu_attr(window, names):
    for n in names:
        a = getattr(window, n, None)
        if a is not None:
            return a
    return None



def _ensure_delete_column(window):
    tbl = _get_qtable(window)
    if not tbl:
        return None
    # If first header is already a checkbox marker, keep it
    hdr = tbl.horizontalHeaderItem(0).text() if tbl.horizontalHeaderItem(0) else ""
    if hdr != "✓":
        tbl.insertColumn(0)
        from PyQt6.QtWidgets import QTableWidgetItem
        tbl.setHorizontalHeaderItem(0, QTableWidgetItem("✓"))
        for r in range(tbl.rowCount()):
            it = QTableWidgetItem()
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked)
            tbl.setItem(r, 0, it)
    return 0

def _delete_selected(window):
    tbl = _get_qtable(window)
    if not tbl:
        return
    # ensure column exists then collect checked
    _ensure_delete_column(window)
    rows = []
    for r in range(tbl.rowCount()):
        it = tbl.item(r, 0)
        if it and it.checkState() == Qt.CheckState.Checked:
            rows.append(r)
    if not rows:
        try:
            QMessageBox.information(window, "O'chirish", "Hech narsa tanlanmadi.")
        except Exception:
            pass
        return
    # delete from bottom to top
    for r in reversed(rows):
        tbl.removeRow(r)
    try:
        QMessageBox.information(window, "O'chirish", f"{len(rows)} ta qator o'chirildi.")
    except Exception:
        pass

def _wire_delete(window):
    # Try to bind delete action/button
    for name in ["actionDelete","actionOchirish","btnDelete","btnOchirish"]:
        act = getattr(window, name, None)
        if act:
            try:
                act.triggered.connect(lambda: (_ensure_delete_column(window), _delete_selected(window)))
            except Exception:
                try:
                    act.clicked.connect(lambda: (_ensure_delete_column(window), _delete_selected(window)))
                except Exception:
                    pass

def _refresh_status_colors(window):
    # If there are 'Status' and 'Ping' columns, colorize + text
    tbl = _get_qtable(window)
    if not tbl:
        return
    headers = [tbl.horizontalHeaderItem(c).text().lower() if tbl.horizontalHeaderItem(c) else "" for c in range(tbl.columnCount())]
    try:
        c_status = next(i for i,h in enumerate(headers) if "holat" in h or "status" in h)
    except StopIteration:
        return
    try:
        c_ping = next(i for i,h in enumerate(headers) if "ping" in h)
    except StopIteration:
        c_ping = None
    for r in range(tbl.rowCount()):
        status_item = tbl.item(r, c_status)
        if not status_item: 
            continue
        txt = status_item.text().strip().lower()
        from PyQt6.QtGui import QColor, QBrush
        color = QColor(0,160,0) if txt == "online" else QColor(200,0,0)
        status_item.setForeground(QBrush(color))
        if c_ping is not None:
            ping_item = tbl.item(r, c_ping)
            if ping_item and ping_item.text().strip() and ping_item.text().strip() != "...":
                # keep as is; else leave empty
                pass

def integrate(window):

    # Auto-bound: btn_scan, actionScan, action_skan, actionSkanerlash
    try:
        act = getattr(window, "btn_scan", None)
        if act:
            try:
                act.triggered.connect(lambda: None or (_ for _ in ()).throw(Exception()))
            except Exception:
                try:
                    act.clicked.connect(lambda: None or (_ for _ in ()).throw(Exception()))
                except Exception:
                    pass
    except Exception:
        pass
    try:
        act = getattr(window, "actionScan", None)
        if act:
            try:
                act.triggered.connect(lambda: None or (_ for _ in ()).throw(Exception()))
            except Exception:
                try:
                    act.clicked.connect(lambda: None or (_ for _ in ()).throw(Exception()))
                except Exception:
                    pass
    except Exception:
        pass
    try:
        act = getattr(window, "action_skan", None)
        if act:
            try:
                act.triggered.connect(lambda: None or (_ for _ in ()).throw(Exception()))
            except Exception:
                try:
                    act.clicked.connect(lambda: None or (_ for _ in ()).throw(Exception()))
                except Exception:
                    pass
    except Exception:
        pass
    try:
        act = getattr(window, "actionSkanerlash", None)
        if act:
            try:
                act.triggered.connect(lambda: None or (_ for _ in ()).throw(Exception()))
            except Exception:
                try:
                    act.clicked.connect(lambda: None or (_ for _ in ()).throw(Exception()))
                except Exception:
                    pass
    except Exception:
        pass

    # Auto-bound: btn_report, action_report, actionReport, actionXisobot
    try:
        act = getattr(window, "btn_report", None)
        if act:
            try:
                act.triggered.connect(lambda: _open_report(window))
            except Exception:
                try:
                    act.clicked.connect(lambda: _open_report(window))
                except Exception:
                    pass
    except Exception:
        pass
    try:
        act = getattr(window, "action_report", None)
        if act:
            try:
                act.triggered.connect(lambda: _open_report(window))
            except Exception:
                try:
                    act.clicked.connect(lambda: _open_report(window))
                except Exception:
                    pass
    except Exception:
        pass
    try:
        act = getattr(window, "actionReport", None)
        if act:
            try:
                act.triggered.connect(lambda: _open_report(window))
            except Exception:
                try:
                    act.clicked.connect(lambda: _open_report(window))
                except Exception:
                    pass
    except Exception:
        pass
    try:
        act = getattr(window, "actionXisobot", None)
        if act:
            try:
                act.triggered.connect(lambda: _open_report(window))
            except Exception:
                try:
                    act.clicked.connect(lambda: _open_report(window))
                except Exception:
                    pass
    except Exception:
        pass
    # status colors refresher
    QTimer.singleShot(0, lambda: _refresh_status_colors(window))
    timer = QTimer(window)
    timer.setInterval(2000)
    timer.timeout.connect(lambda: _refresh_status_colors(window))
    try:
        window._addons_timer = timer
        timer.start()
    except Exception:
        pass
    try:
        if ActivationDialog.is_pro():
            window.statusBar().showMessage("IP MONITOR 2025 Pro")
        else:
            days = ActivationDialog.days_left_demo()
            window.statusBar().showMessage(f"IP MONITOR 2025 DEMO — {days} kun qoldi")
    except Exception:
        pass

    a_report = _menu_attr(window, ["actionReport", "actionXisobot", "btnReport"])
    if a_report:
        try:
            a_report.triggered.connect(lambda: _open_report(window))
        except Exception:
            try:
                a_report.clicked.connect(lambda: _open_report(window))
            except Exception:
                pass

    a_hist = _menu_attr(window, ["actionHistory", "actionTarixGrafikasi", "btnHistory"])
    if a_hist:
        try:
            a_hist.triggered.connect(lambda: HistoryDialog(window, group_stats_provider=lambda: _provider_from_table(window)).exec())
        except Exception:
            try:
                a_hist.clicked.connect(lambda: HistoryDialog(window, group_stats_provider=lambda: _provider_from_table(window)).exec())
            except Exception:
                pass

    a_groups = _menu_attr(window, ["actionGroups", "actionGuruhQoshish", "btnGroups"])
    if a_groups:
        def open_groups():
            groups = getattr(window, "groups", [])
            divs = getattr(window, "divisions", [])
            dlg = GroupManagerDialog(window, groups=groups, divisions=divs)
            def updated(gs, ds):
                try:
                    window.groups = gs
                    window.divisions = ds
                    if hasattr(window, "on_groups_updated"):
                        window.on_groups_updated(gs, ds)
                except Exception:
                    pass
            dlg.groups_updated.connect(updated)
            dlg.exec()
        try:
            a_groups.triggered.connect(open_groups)
        except Exception:
            try:
                a_groups.clicked.connect(open_groups)
            except Exception:
                pass

    for name, theme in [("actionThemeWindows","windows"),("actionThemeDark","dark"),("actionThemeLight","light"),
                        ("actionMavzuWindows","windows"),("actionMavzuTungi","dark"),("actionMavzuKunduzgi","light")]:
        act = getattr(window, name, None)
        if act:
            try:
                act.triggered.connect(lambda checked=False, th=theme: set_theme_and_apply(QApplication.instance(), th))
            except Exception:
                pass

    for name, code in [("actionLangUZ","uz"),("actionLangRU","ru"),("actionLangEN","en"),
                       ("actionTilUZ","uz"),("actionTilRU","ru"),("actionTilEN","en")]:
        act = getattr(window, name, None)
        if act:
            try:
                act.triggered.connect(lambda checked=False, c=code: (_set_lang(window, c)))
            except Exception:
                pass

    a_act = _menu_attr(window, ["actionActivate", "actionAktivatsiya"])
    if a_act:
        handler = lambda: ActivationDialog(window).exec()
        try:
            a_act.triggered.connect(handler)
        except Exception:
            try:
                a_act.clicked.connect(handler)
            except Exception:
                pass

    a_upd = _menu_attr(window, ["actionUpdate", "actionYangilash"])
    if a_upd:
        def do_update():
            info = check_updates()
            if info and info.get("found"):
                QMessageBox.information(window, "Update", f'Yangi versiya: {info.get("version")} topildi. O\'rnatish fayli yoningizda.')
            else:
                QMessageBox.information(window, "Update", "Yangi versiya aniqlanmadi.")
        try:
            a_upd.triggered.connect(do_update)
        except Exception:
            try:
                a_upd.clicked.connect(do_update)
            except Exception:
                pass

    a_about = _menu_attr(window, ["actionAbout", "actionDasturHaqida"])
    if a_about:
        handler = lambda: AboutDialog(window).exec()
        try:
            a_about.triggered.connect(handler)
        except Exception:
            try:
                a_about.clicked.connect(handler)
            except Exception:
                pass

    a_scan = _menu_attr(window, ["actionScan", "actionSkanerlash", "btnScan"])
    if a_scan:
        def open_scan():
            existing = set()
            for d in _collect_rows(window):
                if d.get("ip"): existing.add(d["ip"])
            groups = getattr(window, "groups", [])
            divisions = getattr(window, "divisions", [])
            dlg = ScanDialog(window, existing_ips=existing, groups=groups, divisions=divisions)
            def add_list(devs):
                if hasattr(window, "add_devices_from_scan"):
                    window.add_devices_from_scan(devs)
                else:
                    tbl = _get_qtable(window)
                    if not tbl: return
                    for d in devs:
                        r = tbl.rowCount(); tbl.insertRow(r)
                        from PyQt6.QtWidgets import QTableWidgetItem
                        vals = [d.get("group",""), d.get("division",""), d.get("name",""), d.get("ip",""), "Offline", "", ""]
                        for c, val in enumerate(vals):
                            try:
                                tbl.setItem(r, c, QTableWidgetItem(str(val)))
                            except Exception:
                                pass
            dlg.devices_selected.connect(add_list)
            dlg.add_one_requested.connect(lambda ip: _open_device_dialog(window, ip))
            dlg.exec()
        try:
            a_scan.triggered.connect(open_scan)
        except Exception:
            try:
                a_scan.clicked.connect(open_scan)
            except Exception:
                pass

def _open_report(window):
    dlg = ReportDialog(window)
    def do_now(fmt, folder):
        rows = _collect_rows(window)
        if fmt == "xlsx":
            import os, time
            path = os.path.join(folder, f"report_{int(time.time())}.xlsx")
            ReportDialog.save_status_to_xlsx(path, rows)
            try:
                QMessageBox.information(window, "OK", "XLSX saqlandi.")
            except Exception:
                pass
        else:
            try:
                QMessageBox.information(window, "OK", f"{fmt.upper()} uchun generatorni keyin ulaymiz.")
            except Exception:
                pass
    dlg.generate_now.connect(do_now)
    dlg.exec()

def _open_device_dialog(window, preset_ip=None):
    groups = getattr(window, "groups", [])
    divisions = getattr(window, "divisions", [])
    existing = set(d["ip"] for d in _collect_rows(window) if d.get("ip"))
    dlg = DeviceDialog(window, groups=groups, divisions=divisions, existing_ips=existing, preset_ip=preset_ip)
    if dlg.exec():
        data = dlg.result_data()
        if hasattr(window, "add_single_device"):
            window.add_single_device(data)
        else:
            tbl = _get_qtable(window)
            if tbl:
                r = tbl.rowCount(); tbl.insertRow(r)
                from PyQt6.QtWidgets import QTableWidgetItem
                vals = [data.get("group",""), data.get("division",""), data.get("name",""), data.get("ip",""), "Offline", "", ""]
                for c, val in enumerate(vals):
                    try:
                        tbl.setItem(r, c, QTableWidgetItem(str(val)))
                    except Exception:
                        pass

def _set_lang(window, code):
    set_language(code)
    if hasattr(window, "retranslate_ui"):
        try:
            window.retranslate_ui()
        except Exception:
            pass
