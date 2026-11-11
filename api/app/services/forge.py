"""Tutor Forge: verify workshop parts by running pytest on the learner's workspace, and run the tutor.

Security: this executes code the learner wrote on their own machine. It is enabled only in AUTH_MODE=local
(single learner) unless FORGE_ALLOW_EXEC=1 is set explicitly; never enable it on a shared multi-user server
without a sandbox (see lesson sec-03).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..config import get_settings

SUMMARY = re.compile(r"(\d+) (passed|failed|error|errors)")


@dataclass
class VerifyResult:
    passed: bool
    passed_tests: int
    total_tests: int
    output: str


def execution_allowed() -> bool:
    return get_settings().auth_mode == "local" or os.environ.get("FORGE_ALLOW_EXEC") == "1"


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["FORGE_DIR"] = str(get_settings().forge_dir / "workspace")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def verify(part: m.ForgePart) -> VerifyResult:
    s = get_settings()
    test_path = s.forge_dir / "tests" / part.test
    cmd = [sys.executable, "-m", "pytest", str(test_path), "-q", "-p", "no:cacheprovider", "--tb=short", "--no-header", "-rN"]
    try:
        proc = subprocess.run(cmd, cwd=s.forge_dir, env=_env(), capture_output=True, text=True, timeout=s.forge_timeout_seconds, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return VerifyResult(False, 0, 0, f"Timed out after {s.forge_timeout_seconds}s — check for infinite loops.")
    out = (proc.stdout + proc.stderr)[-6000:]
    counts = {"passed": 0, "failed": 0, "error": 0}
    for n, kind in SUMMARY.findall(out):
        counts["error" if kind.startswith("error") else kind] += int(n)
    total = counts["passed"] + counts["failed"] + counts["error"]
    return VerifyResult(proc.returncode == 0 and total > 0, counts["passed"], total, out)


def record(db: Session, user_id: int, part: m.ForgePart, result: VerifyResult) -> m.ForgeProgress:
    fp = db.scalar(select(m.ForgeProgress).where(m.ForgeProgress.user_id == user_id, m.ForgeProgress.part_id == part.id))
    if fp is None:
        fp = m.ForgeProgress(user_id=user_id, part_id=part.id, passed=False, attempts=0, passed_tests=0, total_tests=0, last_output="")
        db.add(fp)
    fp.attempts += 1
    fp.passed = fp.passed or result.passed  # a pass is permanent; later edits are re-verified by the tutor at runtime
    fp.passed_tests, fp.total_tests, fp.last_output = result.passed_tests, result.total_tests, result.output
    fp.verified_at = datetime.now(timezone.utc)
    return fp


def status(db: Session, user_id: int) -> dict:
    parts = list(db.scalars(select(m.ForgePart).order_by(m.ForgePart.order)))
    done = {fp.part_id: fp for fp in db.scalars(select(m.ForgeProgress).where(m.ForgeProgress.user_id == user_id))}
    passed = [p.id for p in parts if done.get(p.id) and done[p.id].passed]
    reveal_id = parts[-1].id if parts else None
    return {"parts": parts, "progress": done, "passed": passed, "revealed": reveal_id in passed if reveal_id else False, "total": len(parts)}


def course_documents(db: Session, lesson_scope: str | None = None) -> list[dict]:
    """Course material the tutor may ground on: authored lesson sections + objectives of every lesson."""
    docs = []
    q = select(m.Lesson).order_by(m.Lesson.global_order)
    if lesson_scope:
        lesson = db.get(m.Lesson, lesson_scope)
        if lesson:
            q = q.where(m.Lesson.module_id == lesson.module_id)
    for lesson in db.scalars(q):
        parts = [lesson.title, "Objectives: " + "; ".join(lesson.objectives)]
        if lesson.overview:
            parts += [lesson.overview.get("what", ""), lesson.overview.get("why", "")]
        for sec in lesson.sections:
            if sec.get("body"):
                parts.append(f"{sec['title']}. {sec['body']}")
        docs.append({"id": lesson.id, "title": lesson.title, "text": "\n".join(parts)})
    return docs


def ask(question: str, documents: list[dict], k: int = 4) -> dict:
    s = get_settings()
    payload = json.dumps({"question": question, "documents": documents, "k": k})
    try:
        proc = subprocess.run(
            [sys.executable, str(s.forge_dir / "runner.py")], input=payload, cwd=s.forge_dir, env=_env(),
            capture_output=True, text=True, timeout=max(90, s.forge_timeout_seconds), encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "The tutor took too long to answer (your generate/rag code may be slow or the model unreachable)."}
    if proc.returncode != 0:
        tail = proc.stderr.strip().splitlines()[-12:]
        return {"ok": False, "error": "Your tutor code raised an error:\n" + "\n".join(tail)}
    try:
        return {"ok": True, **json.loads(proc.stdout)}
    except json.JSONDecodeError:
        return {"ok": False, "error": "The tutor runner printed something that isn't JSON — remove print() calls from your workspace modules."}
