from __future__ import annotations
import os, sys
from PyQt6.QtCore import QUrl
try:
    from PyQt6.QtMultimedia import QSoundEffect
except Exception:
    QSoundEffect = None  # type: ignore

class AudioAlert:
    def __init__(self, wav_path: str | None):
        self.wav_path = wav_path if wav_path and os.path.exists(wav_path) else None
        self._effect = None
        if QSoundEffect and self.wav_path:
            try:
                eff = QSoundEffect()
                eff.setSource(QUrl.fromLocalFile(os.path.abspath(self.wav_path)))
                eff.setLoopCount(1)
                eff.setVolume(1.0)
                self._effect = eff
            except Exception:
                self._effect = None

    def play(self):
        # First: Qt
        if self._effect:
            try:
                self._effect.play()
                return
            except Exception:
                pass
        # Windows fallback
        if sys.platform.startswith("win"):
            try:
                import winsound
                if self.wav_path and os.path.exists(self.wav_path):
                    winsound.PlaySound(self.wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                else:
                    winsound.MessageBeep(winsound.MB_ICONHAND)
                return
            except Exception:
                pass
        # Last resort: bell
        try:
            print("\a", end="", flush=True)
        except Exception:
            pass
