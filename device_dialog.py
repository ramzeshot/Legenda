from __future__ import annotations
import ipaddress
from typing import Optional, List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QLineEdit,
    QSpinBox, QCheckBox, QHBoxLayout, QPushButton, QMessageBox
)
from translations import tr
from app_lists import DEFAULT_GROUPS, DEFAULT_DIVISIONS

class DeviceDialog(QDialog):
    def __init__(self, groups: Optional[List[str]] = None, parent=None, device_data: Optional[dict] = None,
                 prefill_ip: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle(tr("device_add_edit_title"))
        self.resize(420, 360)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(tr("group_label")))
        self.combo_group = QComboBox(self); self.combo_group.setEditable(True)
        self.combo_group.addItems(groups or DEFAULT_GROUPS)
        layout.addWidget(self.combo_group)

        layout.addWidget(QLabel(tr("division_label")))
        self.combo_division = QComboBox(self); self.combo_division.setEditable(True)
        self.combo_division.addItems(DEFAULT_DIVISIONS)
        layout.addWidget(self.combo_division)

        layout.addWidget(QLabel(tr("device_name_label")))
        self.edit_name = QLineEdit(self); layout.addWidget(self.edit_name)

        layout.addWidget(QLabel(tr("ip_label")))
        self.edit_ip = QLineEdit(self); self.edit_ip.setPlaceholderText("192.168.1.1"); layout.addWidget(self.edit_ip)

        layout.addWidget(QLabel(tr("interval_label")))
        self.spin_interval = QSpinBox(self); self.spin_interval.setRange(1, 3600); self.spin_interval.setValue(30)
        layout.addWidget(self.spin_interval)

        self.check_alert = QCheckBox(tr("audio_alert_label")); layout.addWidget(self.check_alert)

        btns = QHBoxLayout()
        self.btn_ok = QPushButton(tr("ok")); self.btn_cancel = QPushButton(tr("cancel"))
        btns.addWidget(self.btn_ok); btns.addWidget(self.btn_cancel); layout.addLayout(btns)
        self.btn_ok.clicked.connect(self.on_ok); self.btn_cancel.clicked.connect(self.reject)

        if device_data:
            self.combo_group.setCurrentText(str(device_data.get("group","")))
            self.combo_division.setCurrentText(str(device_data.get("division","")))
            self.edit_name.setText(str(device_data.get("name","")))
            self.edit_ip.setText(str(device_data.get("ip","")))
            try: self.spin_interval.setValue(int(device_data.get("interval",30)))
            except Exception: pass
            self.check_alert.setChecked(bool(device_data.get("alert", False)))

        if prefill_ip:
            self.edit_ip.setText(prefill_ip)

    def on_ok(self):
        ip_text = self.edit_ip.text().strip()
        try:
            ipaddress.ip_address(ip_text)
        except Exception:
            QMessageBox.critical(self, tr("error"), tr("enter_valid_ip")); return
        if not self.edit_name.text().strip():
            QMessageBox.warning(self, tr("warning"), tr("enter_device_name")); return
        self.accept()

    def get_data(self) -> dict:
        return {
            "group": self.combo_group.currentText().strip() or "Default",
            "division": self.combo_division.currentText().strip(),
            "name": self.edit_name.text().strip(),
            "ip": self.edit_ip.text().strip(),
            "interval": int(self.spin_interval.value()),
            "alert": bool(self.check_alert.isChecked()),
        }
