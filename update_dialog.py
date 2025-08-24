from __future__ import annotations
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import QDateTime

APP_VERSION = "1.0.0"

class UpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yangilanish")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Hozirgi versiya: {APP_VERSION}"))
        lay.addWidget(QLabel(f"Build vaqti: {QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')}"))
        lay.addWidget(QLabel("Hozircha eng so‘nggi versiyadasiz."))
        btn = QPushButton("Yopish")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn)
