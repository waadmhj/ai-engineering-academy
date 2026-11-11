"""Check that every topic in content.md (the AI Engineer Roadmap) is covered by the curriculum.

A leaf topic is covered when a lesson (content/curriculum/*.yaml) or a project (content/projects.yaml)
lists it in `covers` as "<domain#>: <topic>". A parent topic (e.g. "Python") is covered when all
of its children are. Unknown `covers` entries (typos) are reported too.

Usage: python scripts/check_coverage.py      (exit 1 on any gap)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LINE = re.compile(r"^(?P<prefix>[│ ]*)(?:├──|└──)\s+(?P<name>.+?)\s*$")
DOMAIN = re.compile(r"^(\d+)\.\s+(.+)$")


def parse_roadmap(path: Path) -> tuple[dict[int, str], dict[tuple[int, str], list[str]]]:
    """Return {domain#: title} and {(domain#, topic): [children]} for every topic node."""
    domains: dict[int, str] = {}
    children: dict[tuple[int, str], list[str]] = {}
    stack: list[tuple[int, str]] = []  # (depth, name)
    current = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = LINE.match(raw)
        if not m:
            continue
        depth = len(m.group("prefix")) // 4
        name = m.group("name")
        if depth == 0:
            d = DOMAIN.match(name)
            if not d:
                continue
            current = int(d.group(1))
            domains[current] = d.group(2)
            stack = []
            continue
        stack = [s for s in stack if s[0] < depth]
        children.setdefault((current, name), [])
        if stack:
            children[(current, stack[-1][1])].append(name)
        stack.append((depth, name))
    return domains, children


def collect_covers() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for f in sorted((ROOT / "content" / "curriculum").glob("*.yaml")):
        stage = yaml.safe_load(f.read_text(encoding="utf-8"))
        for mod in stage["modules"]:
            for lesson in mod["lessons"]:
                found += [(c, f"lesson {lesson['id']}") for c in lesson.get("covers", [])]
    proj = ROOT / "content" / "projects.yaml"
    if proj.exists():
        for p in yaml.safe_load(proj.read_text(encoding="utf-8")):
            found += [(c, f"project {p['id']}") for c in p.get("covers", [])]
    return found


def coverage_report() -> dict:
    domains, tree = parse_roadmap(ROOT / "content.md")
    covered: dict[tuple[int, str], list[str]] = {}
    unknown: list[str] = []
    for entry, where in collect_covers():
        m = re.match(r"^(\d+):\s*(.+)$", entry)
        key = (int(m.group(1)), m.group(2).strip()) if m else None
        if key not in tree:
            unknown.append(f"{entry!r} in {where}")
            continue
        covered.setdefault(key, []).append(where)

    def is_covered(key: tuple[int, str]) -> bool:
        kids = tree[key]
        if key in covered:
            return True
        return bool(kids) and all(is_covered((key[0], k)) for k in kids)

    missing = [f"{d}: {t}" for (d, t) in tree if not is_covered((d, t))]
    per_domain = {}
    for d, title in domains.items():
        keys = [k for k in tree if k[0] == d]
        per_domain[d] = {"title": title, "topics": len(keys), "covered": sum(is_covered(k) for k in keys)}
    return {"domains": per_domain, "missing": missing, "unknown": unknown, "total": len(tree)}


def main() -> int:
    r = coverage_report()
    for d, info in r["domains"].items():
        flag = "OK " if info["covered"] == info["topics"] else "GAP"
        print(f"{flag} {d:>2}. {info['title']:<42} {info['covered']}/{info['topics']}")
    if r["unknown"]:
        print("\nUnknown covers entries (typo or not in roadmap):")
        print("\n".join("  - " + u for u in r["unknown"]))
    if r["missing"]:
        print("\nUncovered roadmap topics:")
        print("\n".join("  - " + m for m in r["missing"]))
    print(f"\n{r['total'] - len(r['missing'])}/{r['total']} roadmap topics covered")
    return 1 if (r["missing"] or r["unknown"]) else 0


if __name__ == "__main__":
    sys.exit(main())
