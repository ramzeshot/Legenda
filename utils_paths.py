from __future__ import annotations
import os, sys

def resource_path(*parts: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, *parts)
