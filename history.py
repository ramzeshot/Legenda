from __future__ import annotations
import os, csv, time

def ensure_log(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(["ts","group","division","name","ip","online","ms"])

def log_status_change(path: str, group: str, division: str, name: str, ip: str, online: bool, ms: int):
    ensure_log(path)
    with open(path, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow([int(time.time()), group, division, name, ip, int(online), ms])
