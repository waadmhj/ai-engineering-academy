"""Pydantic schemas that validate everything under content/ before it reaches the database."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Level = Literal["beginner", "intermediate", "advanced"]
QuestionKind = Literal["mcq", "multi", "short", "technical", "practical", "scenario"]
SectionKind = Literal["simple", "technical", "diagram", "math", "code", "real_world", "mistakes", "when"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResourceIn(Strict):
    id: str
    title: str
    provider: str
    type: Literal["video", "book", "docs", "course", "paper", "interactive", "article"]
    level: Level
    duration: str
    language: str = "en"
    cost: Literal["free", "paid", "audit", "freemium"]
    url: str
    why: str
    authors: str | None = None
    year: int | None = None
    isbn: str | None = None
    embed: dict[str, str] = Field(default_factory=dict)
    chapters: list[Any] = Field(default_factory=list)
    summary: str | None = None
    impact: str | None = None

    @field_validator("url")
    @classmethod
    def _https(cls, v: str) -> str:
        if not v.startswith(("https://", "http://")):
            raise ValueError("url must be absolute http(s)")
        return v

    @model_validator(mode="after")
    def _paper_fields(self):
        if self.type == "paper" and not (self.summary and self.impact):
            raise ValueError(f"paper {self.id} needs a simplified summary and an impact statement")
        return self


class LessonRef(Strict):
    id: str
    title: str
    minutes: int = Field(gt=0, le=600)
    level: Level
    covers: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(min_length=1)
    resources: list[str] = Field(default_factory=list)
    workshop: str | None = None

    def resource_links(self) -> list[tuple[str, str]]:
        """'id!' → required, 'id' → supplementary."""
        return [(r.rstrip("!"), "required" if r.endswith("!") else "supplementary") for r in self.resources]


class ModuleIn(Strict):
    id: str
    title: str
    summary: str
    prerequisites: list[str] = Field(default_factory=list)
    project: str | None = None
    lessons: list[LessonRef] = Field(min_length=1)


class StageIn(Strict):
    id: str
    order: int
    title: str
    summary: str
    modules: list[ModuleIn]


class Section(Strict):
    kind: SectionKind
    title: str
    body: str | None = None
    svg: str | None = None
    caption: str | None = None

    @model_validator(mode="after")
    def _has_content(self):
        if not (self.body or self.svg):
            raise ValueError(f"section '{self.title}' needs body or svg")
        return self


class ExerciseIn(Strict):
    title: str
    prompt: str
    starter: str | None = None
    expected: str
    hints: list[str] = Field(min_length=1)
    solution: str
    explanation: str
    advanced: str | None = None


class QuestionIn(Strict):
    id: str
    kind: QuestionKind
    prompt: str
    options: list[str] = Field(default_factory=list)
    answer: int | list[int] | None = None
    keywords: list[list[str]] = Field(default_factory=list)
    model_answer: str | None = None
    explanation: str | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.kind == "mcq":
            if not isinstance(self.answer, int) or not (0 <= self.answer < len(self.options)):
                raise ValueError(f"{self.id}: mcq needs options and a valid answer index")
        elif self.kind == "multi":
            if not isinstance(self.answer, list) or not self.answer or any(not 0 <= a < len(self.options) for a in self.answer):
                raise ValueError(f"{self.id}: multi needs a non-empty list of valid indices")
        elif not self.model_answer:
            raise ValueError(f"{self.id}: open questions need a model_answer")
        return self


class Flashcard(Strict):
    front: str
    back: str


class Overview(Strict):
    what: str
    why: str
    where: str
    prerequisites: str


class LessonBody(Strict):
    overview: Overview
    sections: list[Section] = Field(min_length=7)  # maths only "when relevant"
    exercise: ExerciseIn
    quiz: list[QuestionIn] = Field(min_length=5)
    flashcards: list[Flashcard] = Field(min_length=3)

    @model_validator(mode="after")
    def _ladder_complete(self):
        required = {"simple", "technical", "code", "real_world", "mistakes", "when"}
        missing = required - {s.kind for s in self.sections}
        if missing:
            raise ValueError(f"lesson is missing concept-ladder sections: {sorted(missing)}")
        kinds = {q.kind for q in self.quiz}
        if not {"mcq", "scenario"} <= kinds:
            raise ValueError("quiz needs at least MCQ and scenario questions")
        return self


class Milestone(Strict):
    title: str
    deliverables: list[str]


class TechChoice(Strict):
    choice: str
    why: str


class CapstoneSpec(Strict):
    problem: str
    business: list[str]
    functional: list[str]
    nonfunctional: list[str]
    architecture: list[list[str]]
    tech: list[TechChoice]
    database: list[str]
    milestones: list[Milestone]
    decisions: list[str]
    testing: list[str]
    security: list[str]
    evaluation: list[str]
    deployment: list[str]
    monitoring: list[str]
    cost: list[str]


class ProjectIn(Strict):
    id: str
    level: Literal["mini", "module", "capstone", "portfolio"]
    title: str
    summary: str
    hours: int
    module: str | None = None
    covers: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    spec: CapstoneSpec | None = None

    @model_validator(mode="after")
    def _shape(self):
        if self.level in ("capstone", "portfolio") and self.spec is None:
            raise ValueError(f"{self.id}: capstones need a full spec")
        if self.level in ("mini", "module") and not self.requirements:
            raise ValueError(f"{self.id}: mini/module projects need requirements")
        return self


class RubricIn(Strict):
    criterion: str
    weight: int
    levels: dict[str, str]


class ProjectDefaults(Strict):
    documentation: list[str]
    deliverables: list[str]
    rubric: list[RubricIn]


class ForgePartIn(Strict):
    id: str
    order: int
    lesson: str
    title: str
    file: str
    test: str
    functions: list[str]
    task: str
    hints: list[str]
    capability: str


class ForgeIn(Strict):
    reveal_after: str
    parts: list[ForgePartIn]


class InterviewQuestion(QuestionIn):
    track: str
