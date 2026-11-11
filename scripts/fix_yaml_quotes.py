"""Quote plain YAML scalars that would otherwise be mis-parsed (contain ': ', ' #', or start with a reserved char).

Usage: python scripts/fix_yaml_quotes.py <file.yaml> [...]
Only touches single-line `key: value` and `- item` scalars outside block literals (| / >).
"""
import re
import sys
from pathlib import Path

import yaml

RESERVED_START = ("`", "@", "%", "*", "&", "!", "?", ",")
KV = re.compile(r"^(\s*(?:-\s+)?)([A-Za-z_][\w-]*): (.+)$")
ITEM = re.compile(r"^(\s*-\s+)(.+)$")


def needs_quotes(v: str) -> bool:
    if v[0] in "\"'[{|>":
        return False
    return ": " in v or " #" in v or v.startswith(RESERVED_START) or v.endswith(":")


def quote(v: str) -> str:
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def fix(path: Path) -> int:
    out, changed = [], 0
    block_indent = None
    for line in path.read_text(encoding="utf-8").splitlines():
        indent = len(line) - len(line.lstrip())
        if block_indent is not None:
            if line.strip() == "" or indent > block_indent:
                out.append(line)
                continue
            block_indent = None
        m = KV.match(line)
        if m:
            prefix, key, val = m.groups()
            if val.strip() in ("|", ">", "|-", ">-"):
                block_indent = len(prefix)  # column of the key; deeper lines belong to the block
                out.append(line)
                continue
            if needs_quotes(val):
                line = f"{prefix}{key}: {quote(val)}"
                changed += 1
            out.append(line)
            continue
        m = ITEM.match(line)
        if m and not KV.match(line):
            prefix, val = m.groups()
            if needs_quotes(val):
                line = f"{prefix}{quote(val)}"
                changed += 1
        out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    yaml.safe_load(path.read_text(encoding="utf-8"))  # raises if still invalid
    return changed


if __name__ == "__main__":
    for f in sys.argv[1:]:
        try:
            print(f"{f}: {fix(Path(f))} values quoted")
        except yaml.YAMLError as e:
            print(f"{f}: STILL INVALID -> {e}")
