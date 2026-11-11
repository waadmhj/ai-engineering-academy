"""Tutor Forge workshops and the learner-built AI tutor."""
from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models as m
from ..auth import current_user
from ..config import get_settings
from ..db import get_db
from ..services import forge as svc
from ..services.progress import log

router = APIRouter(tags=["forge"])

MODES = {
    "ask": "{q}",
    "simpler": "Explain this in simpler language, with an everyday analogy: {q}",
    "example": "Give another worked example of: {q}",
    "exercise": "Create a short practice exercise (with expected outcome) about: {q}",
    "quiz": "Write three quiz questions with answers to test my understanding of: {q}",
    "tradeoffs": "What are the engineering trade-offs of: {q}",
    "code": "Explain this code line by line: {q}",
}


def _part_out(part: m.ForgePart, fp: m.ForgeProgress | None, lesson_title: str) -> dict:
    return {
        "id": part.id, "order": part.order, "title": part.title, "lesson_id": part.lesson_id, "lesson_title": lesson_title,
        "file": f"forge/workspace/{part.file}", "test": f"forge/tests/{part.test}", "functions": part.functions,
        "task": part.task, "hints": part.hints, "passed": bool(fp and fp.passed), "attempts": fp.attempts if fp else 0,
        "passed_tests": fp.passed_tests if fp else 0, "total_tests": fp.total_tests if fp else 0,
    }


@router.get("/forge/{part_id}")
def get_part(part_id: str, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    part = db.get(m.ForgePart, part_id)
    if part is None:
        raise HTTPException(404, "Workshop not found")
    st = svc.status(db, user.id)
    fp = st["progress"].get(part.id)
    source = (get_settings().forge_dir / "workspace" / part.file).read_text(encoding="utf-8")
    return _part_out(part, fp, db.get(m.Lesson, part.lesson_id).title) | {"source": source, "last_output": fp.last_output if fp else ""}


@router.post("/forge/{part_id}/verify")
def verify_part(part_id: str, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    part = db.get(m.ForgePart, part_id)
    if part is None:
        raise HTTPException(404, "Workshop not found")
    if not svc.execution_allowed():
        raise HTTPException(403, "Workshop verification runs your code, so it is only enabled in local mode (AUTH_MODE=local).")
    result = svc.verify(part)
    fp = svc.record(db, user.id, part, result)
    if result.passed:
        log(db, user.id, "workshop", part.lesson_id, f"Workshop passed: {part.title}")
    db.commit()
    st = svc.status(db, user.id)
    return {"passed": result.passed, "passed_tests": result.passed_tests, "total_tests": result.total_tests, "output": result.output,
            "attempts": fp.attempts, "assembled": len(st["passed"]), "total": st["total"], "revealed": st["revealed"]}


@router.get("/forge/{part_id}/solution")
def part_solution(part_id: str, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    part = db.get(m.ForgePart, part_id)
    if part is None:
        raise HTTPException(404, "Workshop not found")
    fp = svc.status(db, user.id)["progress"].get(part.id)
    if not fp or fp.attempts < 2:
        raise HTTPException(409, "Try verifying your own implementation at least twice before viewing the reference solution.")
    return {"source": (get_settings().forge_dir / "solutions" / part.file).read_text(encoding="utf-8")}


@router.get("/tutor/status")
def tutor_status(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    st = svc.status(db, user.id)
    lessons = {p.lesson_id: db.get(m.Lesson, p.lesson_id).title for p in st["parts"]}
    passed = set(st["passed"])
    if not st["revealed"]:
        # Before the reveal the learner sees only that *something* is being assembled from their workshop work.
        return {"revealed": False, "assembled": len(passed), "total": st["total"], "parts": [
            {"order": p.order, "assembled": p.id in passed, "lesson_id": p.lesson_id if p.id in passed else None, "lesson_title": lessons[p.lesson_id] if p.id in passed else None}
            for p in st["parts"]
        ]}
    return {"revealed": True, "assembled": len(passed), "total": st["total"], "execution_allowed": svc.execution_allowed(),
            "provider": os.environ.get("TUTOR_PROVIDER", "none"),
            "parts": [_part_out(p, st["progress"].get(p.id), lessons[p.lesson_id]) | {"capability": p.capability} for p in st["parts"]],
            "modes": list(MODES)}


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    lesson_id: str | None = None
    scope: Literal["lesson", "course"] = "course"
    mode: Literal["ask", "simpler", "example", "exercise", "quiz", "tradeoffs", "code"] = "ask"


@router.post("/tutor/ask")
def tutor_ask(body: AskIn, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    st = svc.status(db, user.id)
    if not st["revealed"]:
        raise HTTPException(403, "Not available yet.")
    if not svc.execution_allowed():
        raise HTTPException(403, "The tutor runs your own code, so it is only enabled in local mode.")
    question = MODES[body.mode].format(q=body.question)
    docs = svc.course_documents(db, body.lesson_id if body.scope == "lesson" else None)
    result = svc.ask(question, docs)
    if result.get("ok"):
        log(db, user.id, "tutor", body.lesson_id, f"Asked the tutor: {body.question[:80]}")
        db.commit()
    return result
