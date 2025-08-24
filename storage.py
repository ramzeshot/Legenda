from __future__ import annotations
import json
from typing import List
from data_model import Device

def save_project_json(path: str, devices: List[Device]):
    data = [d.__dict__ for d in devices]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_project_json(path: str) -> List[Device]:
    with open(path, 'r', encoding='utf-8') as f:
        arr = json.load(f)
    devs: List[Device] = []
    for d in arr:
        devs.append(Device(**d))
    return devs
