from __future__ import annotations
from typing import List
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit
from data_model import Device

class ReportDialog(QDialog):
    def __init__(self, devices: List[Device], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hisobot")
        t = QTextEdit(self); t.setReadOnly(True)
        t.setText("\n".join(f"{d.group}\t{d.division}\t{d.name}\t{d.ip}\t{'Online' if d.online else 'Offline'}\t{d.last_ms}ms" for d in devices))
        l = QVBoxLayout(self); l.addWidget(t)
