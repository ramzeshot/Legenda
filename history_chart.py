from __future__ import annotations
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel

class HistoryChart(QDialog):
    def __init__(self, log_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tarix (mock)")
        l = QVBoxLayout(self)
        l.addWidget(QLabel("Grafik moduli hali soddalashtirilgan."))
