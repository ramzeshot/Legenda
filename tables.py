from __future__ import annotations
from typing import List, Any
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionProgressBar, QApplication
from data_model import Device

HEADERS = ["Guruh", "Bo‘linma", "Qurilma nomi", "IP manzili", "Holati", "Ping (ms)", "Progress"]

def ms_to_progress(ms: int) -> int:
    try:
        return max(0, min(100, int(100 - (ms / 3))))
    except Exception:
        return 0

class DeviceTableModel(QAbstractTableModel):
    def __init__(self, devices: List[Device]):
        super().__init__()
        self.devices = devices

    # helpers
    def add_device(self, d: Device):
        self.beginInsertRows(QModelIndex(), len(self.devices), len(self.devices))
        self.devices.append(d)
        self.endInsertRows()

    def update_row(self, row: int):
        if 0 <= row < len(self.devices):
            self.dataChanged.emit(self.index(row,0), self.index(row, self.columnCount()-1))

    def remove_row(self, row: int):
        if 0 <= row < len(self.devices):
            self.beginRemoveRows(QModelIndex(), row, row)
            self.devices.pop(row)
            self.endRemoveRows()

    # Qt model
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.devices)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(HEADERS)

    def headerData(self, section: int, orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(HEADERS):
                return HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        if not (0 <= r < len(self.devices)):
            return None
        d = self.devices[r]
        if role == Qt.ItemDataRole.DisplayRole:
            if c == 0: return d.group
            if c == 1: return d.division
            if c == 2: return d.name
            if c == 3: return d.ip
            if c == 4: return "Online" if d.online else "Offline"
            if c == 5:
                ms = getattr(d, "last_ms", 0) or 0
                return ms if ms > 0 else ""
            if c == 6:
                ms = getattr(d, "last_ms", 0) or 0
                return ms_to_progress(ms) if ms > 0 else 0
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if c in (1,3,5,6):
                return int(Qt.AlignmentFlag.AlignCenter)
        return None

class DeviceFilterProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.term = ""
        self.group = "Barchasi"
        self.state = "Barchasi"

    def setFilters(self, term: str, group: str, state: str):
        self.term = term or ""
        self.group = group or "Barchasi"
        self.state = state or "Barchasi"
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        idx = lambda c: self.sourceModel().index(source_row, c, source_parent)
        name = (self.sourceModel().data(idx(2)) or "").lower()
        ip = (self.sourceModel().data(idx(3)) or "").lower()
        grp = self.sourceModel().data(idx(0)) or ""
        state = self.sourceModel().data(idx(4)) or ""
        if self.term:
            t = self.term.lower()
            if t not in name and t not in ip:
                return False
        if self.group and self.group != "Barchasi" and grp != self.group:
            return False
        if self.state == "Online" and state != "Online":
            return False
        if self.state == "Offline" and state != "Offline":
            return False
        return True

class ProgressDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        try:
            val = index.data(Qt.ItemDataRole.DisplayRole)
            v = int(val) if val is not None else 0
        except Exception:
            v = 0
        bar = QStyleOptionProgressBar()
        bar.rect = option.rect
        bar.minimum = 0
        bar.maximum = 100
        bar.progress = max(0, min(100, v))
        bar.text = f"{bar.progress}%"
        bar.textVisible = True
        QApplication.style().drawControl(QApplication.style().ControlElement.CE_ProgressBar, bar, painter)
