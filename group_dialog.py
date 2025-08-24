from __future__ import annotations
from typing import List
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QHBoxLayout, QPushButton, QLineEdit

class GroupDialog(QDialog):
    def __init__(self, groups: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guruhlar")
        self._list = QListWidget(self); self._list.addItems(groups)
        self._edit = QLineEdit(self); self._add = QPushButton("Qo‘shish", self); self._del = QPushButton("O‘chirish", self)
        root = QVBoxLayout(self); root.addWidget(self._list)
        row = QHBoxLayout(); row.addWidget(self._edit); row.addWidget(self._add); row.addWidget(self._del); root.addLayout(row)
        btns = QHBoxLayout(); self._ok = QPushButton("OK"); self._cancel = QPushButton("Bekor"); btns.addWidget(self._ok); btns.addWidget(self._cancel); root.addLayout(btns)
        self._add.clicked.connect(self._on_add); self._del.clicked.connect(self._on_del); self._ok.clicked.connect(self.accept); self._cancel.clicked.connect(self.reject)

    def _on_add(self):
        t = self._edit.text().strip()
        if t: self._list.addItem(t); self._edit.clear()

    def _on_del(self):
        for it in self._list.selectedItems():
            row = self._list.row(it); self._list.takeItem(row)

    def get_groups(self) -> List[str]:
        return [self._list.item(i).text() for i in range(self._list.count())]
