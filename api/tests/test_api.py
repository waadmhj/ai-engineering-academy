"""End-to-end API behaviour on a fresh database seeded from content/."""


def test_health_and_curriculum(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    stages = client.get("/api/curriculum").json()
    assert [s["order"] for s in stages] == [1, 2, 3, 4, 5, 6]
    assert sum(len(m["lessons"]) for s in stages for m in s["modules"]) >= 180
    first = stages[0]["modules"][0]
    assert first["prerequisites_met"] and first["lessons"][0]["id"] == "py-01"


def test_unknown_lesson_404(client):
    assert client.get("/api/lessons/nope").status_code == 404


def test_lesson_hides_answers_and_solution(client):
    lesson = client.get("/api/lessons/py-01").json()
    assert lesson["content_status"] == "authored"
    assert all("answer" not in q and "model_answer" not in q for q in lesson["quiz"])
    assert "solution" not in lesson["exercise"]
    assert any(r["role"] == "required" for r in lesson["resources"])


def test_opening_does_not_complete(client):
    p = client.post("/api/lessons/py-01/open").json()
    assert p["status"] == "in_progress" and p["mastery"] == 0
    r = client.put("/api/lessons/py-01/status", json={"status": "completed"})
    assert r.status_code == 409
    r = client.put("/api/lessons/py-01/status", json={"status": "mastered"})
    assert r.status_code == 409


def _answers(client, lesson_id, correct=True):
    lesson = client.get(f"/api/lessons/{lesson_id}").json()
    out = []
    for q in lesson["quiz"]:
        fb = client.post(f"/api/questions/{q['id']}/check", json={"response": None}).json()
        if q["kind"] == "mcq":
            resp = fb["correct_answer"] if correct else (fb["correct_answer"] + 1) % len(q["options"])
            out.append({"question_id": q["id"], "response": resp})
        elif q["kind"] == "multi":
            out.append({"question_id": q["id"], "response": fb["correct_answer"] if correct else []})
        else:
            text = fb["model_answer"] if correct else "not sure"
            out.append({"question_id": q["id"], "response": text, "self_grade": "correct" if correct else "incorrect"})
    return out


def test_quiz_requires_all_answers_and_self_grades(client):
    answers = _answers(client, "py-01")
    assert client.post("/api/lessons/py-01/quiz", json={"answers": answers[:2]}).status_code == 422
    no_grade = [{k: v for k, v in a.items() if k != "self_grade"} for a in answers]
    assert client.post("/api/lessons/py-01/quiz", json={"answers": no_grade}).status_code == 422


def test_full_mastery_flow(client):
    r = client.post("/api/lessons/py-01/quiz", json={"answers": _answers(client, "py-01", correct=False)}).json()
    assert r["score"] < 0.7 and r["progress"]["status"] == "in_progress"

    r = client.post("/api/lessons/py-01/quiz", json={"answers": _answers(client, "py-01")}).json()
    assert r["score"] == 1.0
    assert r["progress"]["status"] == "completed"  # no exercise yet → not mastered
    assert r["progress"]["can_master"] is False

    assert client.post("/api/lessons/py-01/exercise", json={"code": "x", "self_check": "solved"}).status_code == 422
    ex = client.post("/api/lessons/py-01/exercise", json={"code": "def group_by_tenant(docs, tenants, out=None):\n    ...", "self_check": "solved"}).json()
    assert "solution" in ex and ex["progress"]["status"] == "mastered"

    cards = client.get("/api/flashcards/due").json()
    assert len(cards) >= 3
    rv = client.post(f"/api/flashcards/{cards[0]['id']}/review", json={"grade": 2}).json()
    assert rv["interval_days"] == 1.0


def test_outline_lessons_use_objectives_and_cannot_be_mastered(client):
    lesson = client.get("/api/lessons/py-02").json()
    assert lesson["content_status"] == "outline" and lesson["quiz"] == []
    n = len(lesson["objectives"])
    p = client.put("/api/lessons/py-02/objectives", json={"checked": list(range(n - 1))}).json()
    assert p["status"] == "in_progress" and not p["can_complete"]
    p = client.put("/api/lessons/py-02/objectives", json={"checked": list(range(n))}).json()
    assert p["status"] == "completed" and p["mastery"] <= 0.7
    assert client.put("/api/lessons/py-02/status", json={"status": "mastered"}).status_code == 409


def test_dashboard_and_analytics(client):
    client.post("/api/progress/heartbeat", json={"seconds": 90, "lesson_id": "py-03"})
    d = client.get("/api/dashboard").json()
    assert d["totals"]["completed"] >= 2 and d["totals"]["mastered"] >= 1
    assert d["next"]["id"] == "py-03"
    assert d["totals"]["streak"] == 1
    a = client.get("/api/analytics").json()
    assert a["status_counts"]["mastered"] >= 1 and len(a["study"]) == 30
    assert any(s["domain"] == 1 for s in a["skills"])


def test_revision_and_interview(client):
    session = client.get("/api/revision/session?n=5").json()
    assert len(session["questions"]) == 5
    q = session["questions"][0]
    assert client.post(f"/api/questions/{q['id']}/attempt", json={"response": "x", "mode": "revision"}).status_code in (200, 422)
    tracks = client.get("/api/interview/tracks").json()
    assert {t["id"] for t in tracks} >= {"python", "sql", "rag", "system-design"}


def test_resources_filter_and_search(client):
    videos = client.get("/api/resources?type=video").json()
    assert videos and all(r["type"] == "video" and r["embed"].get("youtube") for r in videos)
    papers = client.get("/api/resources?type=paper").json()
    assert all(p["summary"] and p["impact"] for p in papers)
    hits = client.get("/api/search?q=cosine").json()
    assert any(l["id"] == "emb-02" for l in hits["lessons"])


def test_project_submission_rules(client):
    projects = client.get("/api/projects").json()
    levels = {p["level"] for p in projects}
    assert levels == {"mini", "module", "capstone", "portfolio"}
    cap = client.get("/api/projects/cap-production-rag").json()
    assert len(cap["rubric"]) == 7 and cap["spec"]["decisions"]
    ms = cap["milestones"][0]["id"]
    assert client.put(f"/api/projects/cap-production-rag/milestones/{ms}", json={"done": True}).status_code == 422
    ok = client.put(f"/api/projects/cap-production-rag/milestones/{ms}", json={"done": True, "evidence_url": "https://github.com/me/rag/pull/1"})
    assert ok.status_code == 200
    r = client.put("/api/projects/cap-production-rag/progress", json={"status": "submitted"})
    assert r.status_code == 409


def test_forge_locked_tutor_and_failing_stub(client):
    st = client.get("/api/tutor/status").json()
    assert st["revealed"] is False and st["total"] == 7 and "capability" not in str(st)
    assert client.post("/api/tutor/ask", json={"question": "what is cosine similarity"}).status_code == 403
    part = client.get("/api/forge/forge-1").json()
    assert "def normalize" in part["source"]
    r = client.post("/api/forge/forge-1/verify").json()
    assert r["passed"] is False and r["total_tests"] > 0  # stubs raise NotImplementedError
    assert client.get("/api/forge/forge-1/solution").status_code == 409


def test_status_validation(client):
    assert client.put("/api/lessons/py-01/status", json={"status": "done"}).status_code == 422
    r = client.put("/api/lessons/py-01/status", json={"status": "needs_revision"})
    assert r.status_code == 200 and r.json()["status"] == "needs_revision"
    d = client.get("/api/dashboard").json()
    assert any(item["id"] == "py-01" for item in d["revision_queue"])
