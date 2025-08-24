from __future__ import annotations
import json, os
from typing import List

class GroupsModel:
    def __init__(self, path: str = "groups.json"):
        self.path = path
        self.data = {"groups": {}}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                if "groups" not in self.data or not isinstance(self.data["groups"], dict):
                    self.data = {"groups": {}}
            except Exception:
                self.data = {"groups": {}}

    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def groups(self) -> List[str]:
        return sorted(self.data.get("groups", {}).keys())

    def divisions(self, group: str) -> List[str]:
        return sorted(self.data.get("groups", {}).get(group, []))

    def add_group(self, name: str):
        self.data["groups"].setdefault(name, [])
        self.save()

    def remove_group(self, name: str):
        self.data["groups"].pop(name, None)
        self.save()

    def add_division(self, group: str, division: str):
        self.data["groups"].setdefault(group, [])
        if division not in self.data["groups"][group]:
            self.data["groups"][group].append(division)
        self.save()

    def remove_division(self, group: str, division: str):
        if group in self.data["groups"]:
            self.data["groups"][group] = [d for d in self.data["groups"][group] if d != division]
        self.save()
