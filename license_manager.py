import json, os
from datetime import datetime, timedelta

LICENSE_FILE = "license.json"
CORRECT_KEY = "IPMONITOR-2025-PRO"

def save_license(data: dict):
    with open(LICENSE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_license():
    if not os.path.exists(LICENSE_FILE):
        return {}
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def is_license_valid():
    data = load_license()
    key = data.get("key")
    return key == CORRECT_KEY

def mode_label():
    if is_license_valid():
        return "Pro"
    data = load_license()
    start = data.get("start")
    if start:
        try:
            start_dt = datetime.fromisoformat(start)
            if datetime.now() - start_dt <= timedelta(days=7):
                return "Demo"
        except Exception:
            pass
    return "Expired"

def device_limit():
    if is_license_valid():
        return 99999  # cheklanmagan
    lbl = mode_label()
    if lbl == "Demo":
        return 99999
    else:
        return 5  # faqat 5 ta qurilma
