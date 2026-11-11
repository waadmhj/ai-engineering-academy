"""Load content/ (YAML), validate it, check cross-references, and seed the content tables.

Run directly:  python -m app.content.loader        (validates + seeds)
               python -m app.content.loader --check (validates only)
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .. import models as m
from ..config import get_settings
from .schemas import ForgeIn, InterviewQuestion, LessonBody, ProjectDefaults, ProjectIn, ResourceIn, StageIn


class ContentError(Exception):
    pass


@dataclass
class Content:
    stages: list[StageIn]
    resources: list[ResourceIn]
    lessons: dict[str, LessonBody]
    projects: list[ProjectIn]
    defaults: ProjectDefaults
    forge: ForgeIn
    interview: list[InterviewQuestion] = field(default_factory=list)


def _read(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_content(content_dir: Path | None = None) -> Content:
    root = content_dir or get_settings().content_dir
    errors: list[str] = []

    def parse(model, data, where):
        try:
            return model.model_validate(data)
        except ValidationError as e:
            errors.append(f"{where}: {e}")
            return None

    stages = [parse(StageIn, _read(p), p.name) for p in sorted((root / "curriculum").glob("stage*.yaml"))]
    resources = [parse(ResourceIn, r, f"resources.yaml[{r.get('id')}]") for r in _read(root / "resources.yaml")]
    lessons: dict[str, LessonBody] = {}
    for p in sorted((root / "lessons").glob("*.yaml")):
        body = parse(LessonBody, _read(p), f"lessons/{p.name}")
        if body:
            lessons[p.stem] = body
    projects = [parse(ProjectIn, pr, f"projects.yaml[{pr.get('id')}]") for pr in _read(root / "projects.yaml")]
    defaults = parse(ProjectDefaults, _read(root / "projects_defaults.yaml"), "projects_defaults.yaml")
    forge = parse(ForgeIn, _read(root / "forge.yaml"), "forge.yaml")
    interview_path = root / "interview.yaml"
    interview = [parse(InterviewQuestion, q, f"interview.yaml[{q.get('id')}]") for q in (_read(interview_path) if interview_path.exists() else [])]

    if errors:
        raise ContentError("\n".join(errors))
    content = Content([s for s in stages if s], [r for r in resources if r], lessons, [p for p in projects if p], defaults, forge, [q for q in interview if q])
    _check_references(content)
    return content


def _dupes(ids: list[str]) -> set[str]:
    seen, d = set(), set()
    for i in ids:
        (d if i in seen else seen).add(i)
    return d


def _check_references(c: Content) -> None:
    errs: list[str] = []
    res_ids = {r.id for r in c.resources}
    mod_ids, lesson_ids, order_seen = [], [], []
    for s in sorted(c.stages, key=lambda s: s.order):
        for mod in s.modules:
            mod_ids.append(mod.id)
            for lesson in mod.lessons:
                lesson_ids.append(lesson.id)
                for rid, _ in lesson.resource_links():
                    if rid not in res_ids:
                        errs.append(f"lesson {lesson.id}: unknown resource '{rid}'")
    mod_set, lesson_set = set(mod_ids), set(lesson_ids)
    for name, ids in (("resource", [r.id for r in c.resources]), ("module", mod_ids), ("lesson", lesson_ids), ("project", [p.id for p in c.projects])):
        for d in _dupes(ids):
            errs.append(f"duplicate {name} id '{d}'")
    position = {mid: i for i, mid in enumerate(mod_ids)}
    proj_ids = {p.id for p in c.projects}
    forge_ids = {p.id for p in c.forge.parts}
    for s in c.stages:
        for mod in s.modules:
            for pre in mod.prerequisites:
                if pre not in mod_set:
                    errs.append(f"module {mod.id}: unknown prerequisite '{pre}'")
                elif position[pre] >= position[mod.id]:
                    errs.append(f"module {mod.id}: prerequisite '{pre}' comes later in the sequence")
            if mod.project and mod.project not in proj_ids:
                errs.append(f"module {mod.id}: unknown project '{mod.project}'")
            for lesson in mod.lessons:
                if lesson.workshop and lesson.workshop not in forge_ids:
                    errs.append(f"lesson {lesson.id}: unknown workshop '{lesson.workshop}'")
    for lid in c.lessons:
        if lid not in lesson_set:
            errs.append(f"lessons/{lid}.yaml has no matching lesson in the curriculum")
    for p in c.projects:
        if p.module and p.module not in mod_set:
            errs.append(f"project {p.id}: unknown module '{p.module}'")
        for pre in p.prerequisites:
            if pre not in mod_set:
                errs.append(f"project {p.id}: unknown prerequisite '{pre}'")
    for part in c.forge.parts:
        if part.lesson not in lesson_set:
            errs.append(f"forge {part.id}: unknown lesson '{part.lesson}'")
    if c.forge.reveal_after not in forge_ids:
        errs.append("forge.reveal_after must reference a part id")
    if errs:
        raise ContentError("\n".join(errs))


def seed(db: Session, content: Content) -> dict[str, int]:
    """Replace all content tables with the validated content. Learner-state tables are untouched."""
    for model in (m.LessonResource, m.Exercise, m.Flashcard, m.Question, m.ForgePart, m.RubricCriterion, m.ProjectMilestone, m.Project, m.Lesson, m.Module, m.Stage, m.Resource):
        db.execute(delete(model))
    db.flush()

    for r in content.resources:
        db.add(m.Resource(**r.model_dump()))
    db.flush()

    g = 0
    workshop_of = {p.lesson: p.id for p in content.forge.parts}
    for s in sorted(content.stages, key=lambda s: s.order):
        db.add(m.Stage(id=s.id, order=s.order, title=s.title, summary=s.summary))
        for mi, mod in enumerate(s.modules):
            db.add(m.Module(id=mod.id, stage_id=s.id, order=mi, title=mod.title, summary=mod.summary, prerequisites=mod.prerequisites, project_id=mod.project))
            for li, ref in enumerate(mod.lessons):
                g += 1
                body = content.lessons.get(ref.id)
                lesson = m.Lesson(
                    id=ref.id, module_id=mod.id, order=li, global_order=g, title=ref.title, level=ref.level, minutes=ref.minutes,
                    status="authored" if body else "outline", covers=ref.covers, objectives=ref.objectives,
                    overview=body.overview.model_dump() if body else {}, sections=[x.model_dump(exclude_none=True) for x in body.sections] if body else [],
                    workshop=ref.workshop or workshop_of.get(ref.id),
                )
                db.add(lesson)
                for ri, (rid, role) in enumerate(ref.resource_links()):
                    db.add(m.LessonResource(lesson_id=ref.id, resource_id=rid, role=role, order=ri))
                if body:
                    db.add(m.Exercise(id=f"{ref.id}:ex", lesson_id=ref.id, data=body.exercise.model_dump()))
                    for qi, q in enumerate(body.quiz):
                        db.add(m.Question(id=f"{ref.id}:{q.id}", lesson_id=ref.id, order=qi, kind=q.kind, prompt=q.prompt, options=q.options, answer=q.answer, keywords=q.keywords, model_answer=q.model_answer, explanation=q.explanation))
                    for fi, card in enumerate(body.flashcards):
                        db.add(m.Flashcard(id=f"{ref.id}:fc{fi + 1}", lesson_id=ref.id, front=card.front, back=card.back))
    db.flush()

    for qi, q in enumerate(content.interview):
        db.add(m.Question(id=f"iv:{q.id}", lesson_id=None, track=q.track, order=qi, kind=q.kind, prompt=q.prompt, options=q.options, answer=q.answer, keywords=q.keywords, model_answer=q.model_answer, explanation=q.explanation))

    for pi, p in enumerate(content.projects):
        spec: dict = {"requirements": p.requirements, "decisions": p.decisions}
        if p.spec:
            spec = p.spec.model_dump() | {"documentation": content.defaults.documentation, "deliverables": content.defaults.deliverables}
        db.add(m.Project(id=p.id, level=p.level, module_id=p.module, order=pi, title=p.title, summary=p.summary, hours=p.hours, covers=p.covers, prerequisites=p.prerequisites, spec=spec))
        if p.spec:
            for mi, ms in enumerate(p.spec.milestones):
                db.add(m.ProjectMilestone(id=f"{p.id}:m{mi + 1}", project_id=p.id, order=mi, title=ms.title, deliverables=ms.deliverables))
            for ri, rc in enumerate(content.defaults.rubric):
                db.add(m.RubricCriterion(id=f"{p.id}:r{ri + 1}", project_id=p.id, order=ri, criterion=rc.criterion, weight=rc.weight, levels=rc.levels))
        else:
            for ri, req in enumerate(p.requirements):
                db.add(m.ProjectMilestone(id=f"{p.id}:m{ri + 1}", project_id=p.id, order=ri, title=req, deliverables=[]))

    for part in content.forge.parts:
        db.add(m.ForgePart(id=part.id, order=part.order, lesson_id=part.lesson, title=part.title, file=part.file, test=part.test, functions=part.functions, task=part.task, hints=part.hints, capability=part.capability))
    db.commit()
    return {
        "stages": len(content.stages),
        "modules": sum(len(s.modules) for s in content.stages),
        "lessons": g,
        "authored_lessons": len(content.lessons),
        "resources": len(content.resources),
        "projects": len(content.projects),
        "interview_questions": len(content.interview),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate only")
    args = ap.parse_args()
    try:
        content = load_content()
    except ContentError as e:
        print(f"Content validation failed:\n{e}", file=sys.stderr)
        return 1
    if args.check:
        print("Content OK")
        return 0
    from ..db import Base, SessionLocal, engine

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        print(seed(db, content))
    return 0


if __name__ == "__main__":
    sys.exit(main())
