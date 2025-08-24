from __future__ import annotations

_lang = "uz"

def set_language(lang: str) -> None:
    global _lang
    _lang = lang

_STRINGS = {
    "uz": {
        "file": "Fayl",
        "menu": "Menyu",
        "help": "Yordam",
        "save_project": "Loyihani saqlash…",
        "load_project": "Loyihani yuklash…",
        "report_menu": "Hisobot",
        "add_group": "Guruh qo‘shish",
        "theme": "Mavzu",
        "theme_win": "Windows",
        "theme_dark": "Tungi",
        "theme_light": "Yorug‘",
        "lang": "Til",
        "lang_uz": "O‘zbekcha",
        "lang_ru": "Русский",
        "lang_en": "English",
        "activate": "Aktivatsiya",
        "update": "Yangilash",
        "about": "Dastur haqida",
        "add_device": "Qo‘shish",
        "delete_device": "O‘chirish",
        "report": "Hisobot",
        "start_monitor": "Monitoringni boshlash",
        "stop_monitor": "Monitoringni to‘xtatish",
        "device_add_edit_title": "Qurilma qo‘shish / Tahrirlash",
        "group_label": "Guruh:",
        "division_label": "Bo‘linma:",
        "device_name_label": "Qurilma nomi:",
        "ip_label": "IP manzili:",
        "interval_label": "Ping interval (s):",
        "audio_alert_label": "Ovozli ogohlantirish",
        "ok": "OK",
        "cancel": "Bekor",
        "error": "Xato",
        "enter_valid_ip": "To‘g‘ri IP manzil kiriting!",
        "warning": "Ogohlantirish",
        "enter_device_name": "Qurilma nomini kiriting!",
    }
}

def tr(key: str) -> str:
    try:
        return _STRINGS[_lang][key]
    except Exception:
        return key
