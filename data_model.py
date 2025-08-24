from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Device:
    group: str
    division: str
    name: str
    ip: str
    interval: int = 30
    alert: bool = False
    online: bool = False
    last_ms: int = 0
