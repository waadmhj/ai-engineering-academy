import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.models import CardState, Question
from app.services import grading, srs

ROOT = Path(__file__).resolve().parents[2]


def q(kind, **kw):
    return Question(id="t:q", kind=kind, prompt="p", options=kw.get("options", []), answer=kw.get("answer"), keywords=kw.get("keywords", []), model_answer=kw.get("model_answer"), explanation="e")


def test_mcq():
    assert grading.grade(q("mcq", options=["a", "b"], answer=1), 1).score == 1.0
    assert grading.grade(q("mcq", options=["a", "b"], answer=1), 0).score == 0.0


def test_multi_partial_credit_and_penalty():
    question = q("multi", options=list("abcd"), answer=[0, 2])
    assert grading.grade(question, [0, 2]).score == 1.0
    assert grading.grade(question, [0]).score == 0.5
    assert grading.grade(question, [0, 1]).score == 0.0  # one right, one wrong
    assert grading.grade(question, [1, 3]).score == 0.0


def test_open_requires_self_grade_and_caps_unsupported_claims():
    question = q("technical", keywords=[["identity"], ["value", "equal"]], model_answer="m")
    pending = grading.grade(question, "it checks identity")
    assert pending.score is None and pending.keyword_coverage == 0.5
    assert grading.grade(question, "identity vs value", "correct").score == 1.0
    assert grading.grade(question, "no idea", "correct").score == 0.5  # evidence cap
    assert grading.grade(question, "   ", "partial").score == 0.0
    with pytest.raises(ValueError):
        grading.grade(question, "x", "great")


def _card():
    return CardState(ease=2.5, interval_days=0.0, repetitions=0, lapses=0, reviews=0, correct=0)


def test_srs_intervals_grow_and_lapse_resets():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    c = _card()
    srs.schedule(c, srs.GOOD, now)
    assert c.interval_days == 1.0
    srs.schedule(c, srs.GOOD, now)
    assert c.interval_days == 3.0
    srs.schedule(c, srs.GOOD, now)
    assert c.interval_days == pytest.approx(3.0 * c.ease, rel=0.01)
    srs.schedule(c, srs.AGAIN, now)
    assert c.repetitions == 0 and c.lapses == 1 and c.due_at - now == timedelta(minutes=10)
    assert c.ease >= srs.MIN_EASE


def test_srs_easy_beats_hard():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    a, b = _card(), _card()
    for card, grade in ((a, srs.EASY), (b, srs.HARD)):
        for _ in range(3):
            srs.schedule(card, grade, now)
    assert a.interval_days > b.interval_days
    assert srs.retention([a, b]) == 1.0


def test_roadmap_fully_covered():
    spec = importlib.util.spec_from_file_location("check_coverage", ROOT / "scripts" / "check_coverage.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    report = mod.coverage_report()
    assert report["unknown"] == []
    assert report["missing"] == [], f"uncovered roadmap topics: {report['missing']}"
    assert len(report["domains"]) == 23
