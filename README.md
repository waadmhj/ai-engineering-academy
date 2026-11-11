# AI Engineering Academy

**From Foundations to Production-Ready AI Engineering.**

A learning platform that turns the 23-domain AI Engineer Roadmap (`content.md`) into a university-style
curriculum: **6 stages · 28 modules · 182 lessons**, with curated resources, exercises, assessments with
mastery scoring, spaced-repetition flashcards, revision and interview modes, a projects ladder (mini → module →
13 capstones → portfolio SaaS), progress analytics, and an AI tutor that **you build yourself** inside the course.

```
website/
  content/     curriculum YAML, authored lessons, resources, projects, interview bank, forge spec
  api/         FastAPI + SQLAlchemy backend (SQLite by default, PostgreSQL via DATABASE_URL)
  web/         Next.js 15 + TypeScript + Tailwind v4 frontend
  forge/       Tutor Forge: workspace/ (your code), tests/ (verification), solutions/, runner.py
  scripts/     check_coverage.py (roadmap coverage), verify_resources.py (link checker)
  docs/        PLAN.md (architecture, schema, journeys), STATUS.md, DEPLOYMENT.md
```

## Run it locally

Requirements: Python 3.11+, Node 20+.

**Windows PowerShell** (5.1 does not support `&&`; run each line separately):

```powershell
# Terminal 1: API
cd api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

# Terminal 2: web
cd web
npm run dev                        # http://localhost:3000
```

First-time setup, bash/macOS/Linux:

```bash
# 1) API — terminal 1
cd api
python -m venv .venv
.venv/Scripts/activate            # Windows (macOS/Linux: source .venv/bin/activate)
pip install -e .
cp .env.example .env              # optional; defaults work
uvicorn app.main:app --port 8000  # creates academy.db and seeds content on first start

# 2) Web — terminal 2
cd web
npm install
npm run dev                        # http://localhost:3000
```

After editing anything in `content/`, re-seed (your progress is preserved):

```bash
cd api && python -m app.content.loader          # validate + reseed
python -m app.content.loader --check            # validate only
```

## Tests and checks

```bash
cd api && python -m pytest                      # API, grading, SRS, mastery rules, coverage, tutor reveal
python scripts/check_coverage.py                # every roadmap topic is mapped (331/331)
python scripts/verify_resources.py              # every resource URL / YouTube ID resolves
cd web && npx tsc --noEmit && npm run lint && npm run build
FORGE_DIR=forge/solutions python -m pytest forge/tests   # reference solutions pass all workshop checks
```

## How progress works

* Opening a lesson only marks it **In progress**.
* **Completed**: at least 70% on the knowledge check (full lessons), or every objective self-checked (outline lessons).
* **Mastered**: at least 85% on the check, the exercise submitted, and flashcards not repeatedly failed. Mastery = 60% quiz + 25% exercise + 15% flashcard retention.
* **Needs revision** is set automatically when revision answers or flashcard retention drop below 60%.
* Open answers use active recall: you write an answer, compare it with the model answer, then self-grade. A "correct" self-grade is capped at partial credit if your answer covers fewer than half the key ideas.

## The AI tutor (Tutor Forge)

There is no AI tutor at the start. Seven lessons contain a **Workshop** task: write a small function in
`forge/workspace/` and verify it from the lesson page. The tutor page only shows that *something* is
being assembled. When the last part (RAG, lesson `rag-04`) passes, the tutor unlocks. It runs entirely on
your code (tokenizer → chunker → vectors → BM25 → LLM client → grounded prompt → RAG), answers from the course
material, and cites lessons. Without a model it answers extractively. Set `TUTOR_PROVIDER` / `TUTOR_MODEL`
(openai, anthropic or ollama) in `api/.env` for generated answers. The core platform never depends on an AI API.

Workshop verification runs your code, so it is enabled only in `AUTH_MODE=local` (single learner on your machine).

See `docs/STATUS.md` for what is complete and what remains.
