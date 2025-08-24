from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QInputDialog, QMessageBox, QLabel
)
from groups_model import GroupsModel

class GroupManagerDialog(QDialog):
    def __init__(self, model: GroupsModel, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guruh/Bo‘linmalar")
        self.resize(520, 420)
        self.model = model

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Guruhlar va bo‘linmalar:"))

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nomi"])
        lay.addWidget(self.tree, 1)

        row = QHBoxLayout()
        self.btn_add_group = QPushButton("Guruh qo‘shish")
        self.btn_add_div = QPushButton("Bo‘linma qo‘shish")
        self.btn_del = QPushButton("O‘chirish")
        self.btn_close = QPushButton("Yopish")
        row.addWidget(self.btn_add_group)
        row.addWidget(self.btn_add_div)
        row.addWidget(self.btn_del)
        row.addStretch(1)
        row.addWidget(self.btn_close)
        lay.addLayout(row)

        self.btn_add_group.clicked.connect(self._add_group)
        self.btn_add_div.clicked.connect(self._add_division)
        self.btn_del.clicked.connect(self._delete_selected)
        self.btn_close.clicked.connect(self.accept)

        self._reload()

    def _reload(self):
        self.tree.clear()
        for g in self.model.groups():
            gitem = QTreeWidgetItem([g])
            self.tree.addTopLevelItem(gitem)
            for d in self.model.divisions(g):
                QTreeWidgetItem(gitem, [d])
        self.tree.expandAll()

    def _add_group(self):
        name, ok = QInputDialog.getText(self, "Yangi guruh", "Nom:")
        if ok and name.strip():
            self.model.add_group(name.strip())
            self._reload()

    def _add_division(self):
        it = self.tree.currentItem()
        if not it:
            QMessageBox.information(self, "Ma’lumot", "Iltimos, guruhni tanlang.")
            return
        gname = it.parent().text(0) if it.parent() else it.text(0)
        div, ok = QInputDialog.getText(self, "Yangi bo‘linma", "Nom:")
        if ok and div.strip():
            self.model.add_division(gname, div.strip())
            self._reload()

    def _delete_selected(self):
        it = self.tree.currentItem()
        if not it:
            return
        if it.parent():
            self.model.remove_division(it.parent().text(0), it.text(0))
        else:
            self.model.remove_group(it.text(0))
        self._reload()
