"""Curriculum browsing: stages, modules, lessons, resources and search."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from .. import models as m
from ..auth import current_user
from ..db import get_db
from ..services import forge as forge_svc
from ..services.insights import curriculum, lesson_brief, module_state, prerequisites_met
from ..services.progress import evidence, get_progress, progress_map

router = APIRouter(tags=["curriculum"])


def resource_dict(r: m.Resource) -> dict:
    return {
        "id": r.id, "title": r.title, "provider": r.provider, "type": r.type, "level": r.level, "duration": r.duration,
        "language": r.language, "cost": r.cost, "url": r.url, "why": r.why, "authors": r.authors, "year": r.year,
        "isbn": r.isbn, "embed": r.embed or {}, "chapters": r.chapters or [], "summary": r.summary, "impact": r.impact,
    }


@router.get("/curriculum")
def get_curriculum(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    prog = progress_map(db, user.id)
    stages = curriculum(db)
    modules_by_id = {mod.id: mod for s in stages for mod in s.modules}
    out = []
    for s in stages:
        mods = []
        for mod in s.modules:
            ok, missing = prerequisites_met(mod, modules_by_id, prog)
            mods.append({
                "id": mod.id, "title": mod.title, "summary": mod.summary, "prerequisites": mod.prerequisites, "project_id": mod.project_id,
                "prerequisites_met": ok, "missing_prerequisites": missing, "state": module_state(mod, prog),
                "hours": round(sum(l.minutes for l in mod.lessons) / 60, 1),
                "lessons": [lesson_brief(l, prog.get(l.id)) for l in mod.lessons],
            })
        out.append({"id": s.id, "order": s.order, "title": s.title, "summary": s.summary, "modules": mods})
    return out


@router.get("/modules/{module_id}")
def get_module(module_id: str, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    mod = db.scalar(select(m.Module).where(m.Module.id == module_id).options(selectinload(m.Module.lessons), selectinload(m.Module.stage)))
    if mod is None:
        raise HTTPException(404, "Module not found")
    prog = progress_map(db, user.id)
    modules_by_id = {x.id: x for x in db.scalars(select(m.Module).options(selectinload(m.Module.lessons)))}
    ok, missing = prerequisites_met(mod, modules_by_id, prog)
    project = db.get(m.Project, mod.project_id) if mod.project_id else None
    return {
        "id": mod.id, "title": mod.title, "summary": mod.summary, "stage": {"id": mod.stage.id, "title": mod.stage.title, "order": mod.stage.order},
        "prerequisites": [{"id": pid, "title": modules_by_id[pid].title, "complete": pid not in missing} for pid in mod.prerequisites],
        "prerequisites_met": ok, "state": module_state(mod, prog),
        "project": {"id": project.id, "title": project.title, "level": project.level, "summary": project.summary} if project else None,
        "lessons": [lesson_brief(l, prog.get(l.id)) | {"objectives": l.objectives, "covers": l.covers, "workshop": l.workshop} for l in mod.lessons],
    }


@router.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: str, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    lesson = db.scalar(
        select(m.Lesson).where(m.Lesson.id == lesson_id).options(
            selectinload(m.Lesson.module).selectinload(m.Module.stage), selectinload(m.Lesson.questions), selectinload(m.Lesson.flashcards),
            selectinload(m.Lesson.resource_links).selectinload(m.LessonResource.resource), selectinload(m.Lesson.exercise),
        )
    )
    if lesson is None:
        raise HTTPException(404, "Lesson not found")
    p = get_progress(db, user.id, lesson.id, create=False)
    prev_l = db.scalar(select(m.Lesson).where(m.Lesson.global_order == lesson.global_order - 1))
    next_l = db.scalar(select(m.Lesson).where(m.Lesson.global_order == lesson.global_order + 1))
    ex = lesson.exercise.data if lesson.exercise else None
    submitted = bool(p and db.scalar(select(m.ExerciseSubmission.id).where(m.ExerciseSubmission.user_id == user.id, m.ExerciseSubmission.lesson_id == lesson.id).limit(1)))
    workshop = None
    if lesson.workshop:
        part = db.get(m.ForgePart, lesson.workshop)
        fs = forge_svc.status(db, user.id)
        fp = fs["progress"].get(part.id)
        workshop = {"id": part.id, "title": part.title, "file": f"forge/workspace/{part.file}", "task": part.task, "hints": part.hints,
                    "passed": bool(fp and fp.passed), "attempts": fp.attempts if fp else 0, "test": f"forge/tests/{part.test}"}
    ev = evidence(lesson, p, []) if p else {"can_complete": False, "can_master": False}
    return {
        "id": lesson.id, "title": lesson.title, "level": lesson.level, "minutes": lesson.minutes, "content_status": lesson.status,
        "covers": lesson.covers, "objectives": lesson.objectives, "overview": lesson.overview, "sections": lesson.sections,
        "module": {"id": lesson.module.id, "title": lesson.module.title}, "stage": {"id": lesson.module.stage.id, "title": lesson.module.stage.title, "order": lesson.module.stage.order},
        "exercise": None if ex is None else {k: v for k, v in ex.items() if k not in ("solution", "explanation")} | {"submitted": submitted},
        "quiz": [{"id": q.id, "kind": q.kind, "prompt": q.prompt, "options": q.options} for q in lesson.questions],
        "flashcards": len(lesson.flashcards),
        "resources": [resource_dict(link.resource) | {"role": link.role} for link in lesson.resource_links],
        "workshop": workshop,
        "progress": {
            "status": p.status if p else "not_started", "mastery": p.mastery if p else 0.0, "quiz_best": p.quiz_best if p else None,
            "quiz_last": p.quiz_last if p else None, "exercise_done": p.exercise_done if p else False,
            "objectives_checked": p.objectives_checked if p else [], "seconds_spent": p.seconds_spent if p else 0,
        } | ev,
        "prev": {"id": prev_l.id, "title": prev_l.title} if prev_l else None,
        "next": {"id": next_l.id, "title": next_l.title} if next_l else None,
    }


@router.get("/resources")
def list_resources(
    type: str | None = None, level: str | None = None, cost: str | None = None, q: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db), user: m.User = Depends(current_user),
):
    stmt = select(m.Resource)
    if type:
        stmt = stmt.where(m.Resource.type == type)
    if level:
        stmt = stmt.where(m.Resource.level == level)
    if cost:
        stmt = stmt.where(m.Resource.cost == cost)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(m.Resource.title.ilike(like), m.Resource.provider.ilike(like), m.Resource.why.ilike(like), m.Resource.authors.ilike(like)))
    resources = list(db.scalars(stmt.order_by(m.Resource.type, m.Resource.title)))
    links = db.execute(select(m.LessonResource.resource_id, m.Lesson.id, m.Lesson.title, m.LessonResource.role).join(m.Lesson, m.Lesson.id == m.LessonResource.lesson_id)).all()
    by_res: dict[str, list[dict]] = {}
    for rid, lid, title, role in links:
        by_res.setdefault(rid, []).append({"id": lid, "title": title, "role": role})
    return [resource_dict(r) | {"lessons": by_res.get(r.id, [])} for r in resources]


@router.get("/resources/{resource_id}")
def get_resource(resource_id: str, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    r = db.get(m.Resource, resource_id)
    if r is None:
        raise HTTPException(404, "Resource not found")
    links = db.execute(select(m.Lesson.id, m.Lesson.title, m.LessonResource.role).join(m.LessonResource, m.Lesson.id == m.LessonResource.lesson_id).where(m.LessonResource.resource_id == r.id)).all()
    return resource_dict(r) | {"lessons": [{"id": i, "title": t, "role": role} for i, t, role in links]}


@router.get("/search")
def search(q: str = Query(..., min_length=2, max_length=100), db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    like = f"%{q}%"
    lessons = db.scalars(select(m.Lesson).where(or_(m.Lesson.title.ilike(like), m.Lesson.id.ilike(like))).order_by(m.Lesson.global_order).limit(10))
    modules = db.scalars(select(m.Module).where(m.Module.title.ilike(like)).limit(5))
    resources = db.scalars(select(m.Resource).where(or_(m.Resource.title.ilike(like), m.Resource.provider.ilike(like))).limit(8))
    projects = db.scalars(select(m.Project).where(m.Project.title.ilike(like)).limit(5))
    # topic search across "covers" (JSON) — done in Python for portability between SQLite and Postgres
    ql = q.lower()
    topic_hits = [l for l in db.scalars(select(m.Lesson).order_by(m.Lesson.global_order)) if any(ql in c.lower() for c in l.covers)][:10]
    seen = set()
    lesson_rows = []
    for l in list(lessons) + topic_hits:
        if l.id not in seen:
            seen.add(l.id)
            lesson_rows.append({"id": l.id, "title": l.title, "module_id": l.module_id})
    return {
        "lessons": lesson_rows[:12],
        "modules": [{"id": x.id, "title": x.title} for x in modules],
        "resources": [{"id": x.id, "title": x.title, "type": x.type, "provider": x.provider} for x in resources],
        "projects": [{"id": x.id, "title": x.title, "level": x.level} for x in projects],
    }


@router.get("/roadmap/coverage")
def roadmap_coverage(db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    """Every roadmap topic and where it is taught (lessons or projects)."""
    where: dict[str, list[dict]] = {}
    for l in db.scalars(select(m.Lesson).order_by(m.Lesson.global_order)):
        for c in l.covers:
            where.setdefault(c, []).append({"type": "lesson", "id": l.id, "title": l.title})
    for p in db.scalars(select(m.Project)):
        for c in p.covers:
            where.setdefault(c, []).append({"type": "project", "id": p.id, "title": p.title})
    return where

