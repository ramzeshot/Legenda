# fix_indent.py — satr boshidagi TAB'larni 4 ta bo'shliqqa aylantiradi
import os, sys

root = sys.argv[1] if len(sys.argv) > 1 else "."
for base, _, files in os.walk(root):
    for name in files:
        if not name.endswith(".py"):
            continue
        p = os.path.join(base, name)
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        out = []
        for s in lines:
            i = 0
            while i < len(s) and s[i] in (" ", "\t"):
                i += 1
            prefix, rest = s[:i], s[i:]
            prefix = prefix.replace("\t", "    ")  # faqat boshidagi TAB'lar
            out.append(prefix + rest)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.writelines(out)
print("Indentation normalized (tabs → 4 spaces).")
