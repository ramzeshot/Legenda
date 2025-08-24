from __future__ import annotations
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton

class ActivateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aktivatsiya")
        l=QVBoxLayout(self)
        l.addWidget(QLabel("Aktivatsiya oynasi (mock)."))
        ok = QPushButton("Yopish", self); ok.clicked.connect(self.accept); l.addWidget(ok)
