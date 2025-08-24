from __future__ import annotations

from addons.services.theme import apply_theme
from addons.ui.splash import show_splash
from PyQt6.QtCore import QTimer
import sys
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


# --- IP MONITOR Addons bootstrap ---
try:
    app  # type: ignore
except NameError:
    pass
else:
    try:
        apply_theme(app)
        _splash = show_splash(app, "logo.png", 2200)
    except Exception:
        pass

try:
    window  # type: ignore
except NameError:
    pass
else:
    try:
        from integration_hooks import integrate as _integrate
        QTimer.singleShot(0, lambda: _integrate(window))
    except Exception:
        pass
