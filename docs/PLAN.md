# AI Engineering Academy — Phase 1 Plan

> From Foundations to Production-Ready AI Engineering.

This document is the Phase 1 deliverable required by `prompt.md` §16: architecture, schema,
curriculum organization, user journeys, development phases, and stack justification.
It is kept up to date at the end of every phase (see `docs/STATUS.md`).

---

## 0. Repository inspection (findings)

| Item | Finding | Consequence |
|---|---|---|
| Existing code | None — only `prompt.md` and `content.md` | Greenfield; we set conventions |
| Node / npm | v26 / 11 | Next.js frontend is viable |
| Python | 3.11 | FastAPI backend + learner exercises run locally |
| Docker / PostgreSQL | **Not installed** | SQLite by default; PostgreSQL via `DATABASE_URL` (schema is portable) |
| Git | Installed | Ready to initialise as a repository (`.gitignore` provided) |

---

## 1. Architecture

```
┌──────────────────────────── Browser ────────────────────────────┐
│ Next.js 15 (App Router, React 19, TypeScript, Tailwind v4)      │
│  • Server-rendered pages for curriculum/lessons                 │
│  • Client components for quizzes, flashcards, progress, tutor   │
│  • /api/* is proxied (Next rewrites) → FastAPI                  │
└───────────────────────────────┬─────────────────────────────────┘
                                │ JSON over HTTP (typed client)
┌───────────────────────────────▼─────────────────────────────────┐
│ FastAPI (Python 3.11, Pydantic v2)                              │
│  routers/   curriculum · lessons · progress · assessments       │
│             flashcards · projects · resources · forge · tutor   │
│  services/  mastery · spaced-repetition (SM-2) · recommender    │
│             forge runner · tutor (built by the learner)         │
│  content/   loader: YAML + Markdown → validated models → DB     │
└───────────────┬───────────────────────────────┬─────────────────┘
                │ SQLAlchemy 2.x                │ subprocess (pytest)
┌───────────────▼──────────────┐   ┌────────────▼─────────────────┐
│ SQLite (dev) / PostgreSQL    │   │ forge/  — the learner's own   │
│ content tables (seeded)      │   │ code: text, chunking, ranking │
│ learner-state tables         │   │ vectors, prompting, rag …     │
└──────────────────────────────┘   └──────────────────────────────┘
```

**Content is data, not UI.** All curriculum content lives in `content/` (YAML + Markdown),
is validated by Pydantic on load, and is seeded into the database. Adding a new learning
path = adding YAML files; no component changes.

### Directory layout

```
website/
  content/            curriculum (stages/*.yaml), lessons/<id>/{lesson.md,quiz.yaml,exercise.yaml},
                      resources.yaml, projects.yaml, forge.yaml, interview.yaml
  api/                FastAPI app (app/), tests/, pyproject
  web/                Next.js app (src/app, src/components, src/lib)
  forge/              Tutor Forge: workspace/ (learner edits) + tests/ (verification)
  scripts/            coverage check, resource URL verification
  docs/               PLAN.md, STATUS.md, DEPLOYMENT.md
```

---

## 2. Database schema

Content tables (rebuilt from `content/` on seed — idempotent):

| Table | Key columns |
|---|---|
| `stages` | id, order, title, summary |
| `modules` | id, stage_id, order, title, summary, domains (json), hours, prerequisites (json: module ids) |
| `lessons` | id, module_id, order, title, level, minutes, status (`authored`/`outline`), covers (json: roadmap topics), objectives (json), overview (json), body_md, prerequisites (json) |
| `resources` | id, title, provider, type, level, duration, language, cost, url, embed (json), why, authors, year |
| `lesson_resources` | lesson_id, resource_id, role (`required`/`supplementary`), note (timestamps/chapters) |
| `exercises` | id, lesson_id, title, prompt_md, starter_code, expected, hints (json), solution_code, solution_explanation, advanced_md |
| `questions` | id, lesson_id (nullable for interview bank), kind (`mcq`/`multi`/`short`/`technical`/`practical`/`scenario`), prompt_md, options (json), answer (json), keywords (json), explanation_md, topic, tags |
| `flashcards` | id, lesson_id, front_md, back_md |
| `projects` | id, level (`mini`/`module`/`capstone`/`portfolio`), module_id, title, spec (json: all capstone sections), covers (json) |
| `project_milestones` | id, project_id, order, title, description, deliverables (json) |
| `rubric_criteria` | id, project_id, criterion, weight, levels (json) |
| `forge_stages` | id, order, title, unlock_after_module, module file, test file, capability |

Learner-state tables:

| Table | Key columns |
|---|---|
| `users` | id, email, display_name, password_hash, created_at |
| `lesson_progress` | user_id, lesson_id, status, mastery (0–1), quiz_best, exercise_done, objectives_checked (json), seconds_spent, started_at, completed_at, updated_at |
| `question_attempts` | user_id, question_id, response (json), correct (bool/score), mode (`lesson`/`revision`/`interview`), created_at |
| `exercise_submissions` | user_id, exercise_id, code, self_reported_pass, created_at |
| `card_states` | user_id, flashcard_id, ease, interval_days, repetitions, due_at, lapses, last_grade |
| `project_progress` | user_id, project_id, status, repo_url, notes, rubric_scores (json), started_at, submitted_at |
| `milestone_progress` | user_id, milestone_id, done, evidence_url, updated_at |
| `study_sessions` | user_id, date, seconds (daily rollup → hours + streak) |
| `activity` | user_id, kind, ref_id, detail, created_at |
| `forge_progress` | user_id, stage_id, passed, last_output, verified_at |

**Status rules (server-enforced)** — `not_started`, `in_progress`, `completed`, `needs_revision`, `mastered`:
* Opening a lesson only moves it to `in_progress`.
* `completed` requires quiz best ≥ 70 % (authored lessons) or every objective self-checked + exercise acknowledged (outline lessons).
* `mastered` requires quiz best ≥ 85 % **and** the exercise submitted **and** flashcards for the lesson not lapsed. Outline lessons cannot be mastered.
* `needs_revision` is set automatically when a later quiz/review drops mastery below 60 %, or manually.
* Mastery = 0.6·quiz_best + 0.25·exercise + 0.15·flashcard retention.

---

## 3. Curriculum organisation

23 roadmap domains → **6 stages, 28 modules, 182 lessons**. Every leaf topic in `content.md`
is mapped via a lesson's `covers:` list (or a project's `covers:` for domain 22). This is
**machine-checked** by `scripts/check_coverage.py` (also a pytest) — nothing is silently omitted.

Sequencing deviations from the prompt's initial grouping (to respect prerequisites):

1. **NumPy/Pandas before Mathematics** — maths is taught *with* NumPy, so data tooling comes first.
2. **Domain 2's "Deep Learning Fundamentals" merges into the first deep-learning module** with
   domain 4's perceptron/backprop topics — taught once, properly, from scratch.
3. **Hugging Face ecosystem moves after LLM Fundamentals** — tokenizers make sense only once
   tokenization is understood.
4. **AI Evaluation moves to the end of Stage 3** (right after RAG) — you cannot iterate on RAG,
   agents or fine-tuning without evals; eval-driven development is taught before agents.
5. **Backend Engineering** stays in Stage 5, but REST/HTTP/FastAPI basics are introduced in Stage 1.

| Stage | Modules |
|---|---|
| 1 Engineering Foundations | M01 Python for AI Engineering · M02 Engineering Toolkit (DSA, Git, Linux, HTTP, REST, serialization) · M03 Numerical Python & Data Wrangling · M04 SQL, Pipelines & Dataset Preparation · M05 Mathematics for ML · M06 Machine Learning Fundamentals |
| 2 Deep Learning Foundations | M07 Neural Networks from First Principles · M08 PyTorch & DL Frameworks · M09 Sequence Models, Attention & Transformers · M10 LLM Fundamentals · M11 Hugging Face Ecosystem |
| 3 Building LLM Applications | M12 LLM APIs & Integration · M13 Prompt & Context Engineering · M14 Embeddings & Vector Search · M15 Retrieval-Augmented Generation · M16 AI Evaluation & Testing |
| 4 Advanced AI Systems | M17 AI Agents · M18 Frameworks & Orchestration · M19 Fine-Tuning & Adaptation · M20 Multimodal AI |
| 5 Production AI Engineering | M21 Backend Engineering for AI · M22 Inference Engineering · M23 MLOps & LLMOps · M24 Cloud & DevOps · M25 AI Security & Responsible AI · M26 AI System Design |
| 6 Real-World Engineering & Career | M27 Capstone Studio (13 projects) · M28 Career Preparation |

Projects ladder: **mini** (per lesson cluster) → **module** projects → **capstones** (13, each with the
16 required sections + rubric) → **final portfolio project** (End-to-End Production AI SaaS).

### Lesson anatomy (rendered by the lesson page)
Overview (what / why / where used / prerequisites / time / objectives) → Concept ladder
(simple → technical → diagram → maths → code → real-world → common mistakes → when to use / not) →
Practice (exercise, expected outcome, hints, solution + explanation, advanced challenge) →
Knowledge check (MCQ, technical, practical, short-answer, scenario) → Resources (required vs supplementary).

### Tutor Forge (the "build your own tutor" idea)
There is **no AI tutor at the start**. Selected lessons contain a "Workshop" task that asks the learner
to implement a small, ordinary-looking function in `forge/workspace/` (normalise text, chunk documents,
rank with BM25, cosine similarity, build a grounded prompt, call an LLM, assemble RAG). The platform
verifies each task by running `forge/tests/` and quietly records it. The Tutor page shows a locked,
partially assembled machine (`3 / 7 parts`). When the RAG module begins — where the material gets
heaviest — the final parts click in and the learner discovers the tutor **runs on their own code**,
grounded in the course content. Capabilities grow with each verified part:

| Part | Unlocks after | Learner implements | Tutor capability |
|---|---|---|---|
| 1 | M01 Python | `normalize`, `tokenize` | keyword lookup across lessons |
| 2 | M03 Data | `chunk_text` (size/overlap) | quotes precise passages |
| 3 | M05 Maths | `cosine_similarity`, `top_k` | vector ranking primitive |
| 4 | M06 ML | `bm25_scores` | ranked lexical search |
| 5 | M12 LLM APIs | `generate` (OpenAI/Anthropic/Ollama/none) | natural-language answers |
| 6 | M13 Prompting | `build_grounded_prompt` | cited, grounded prompts |
| 7 | M15 RAG (lesson rag-04) | `retrieve` + `answer` pipeline | full grounded tutor (reveal) |

Without an API key the tutor still works extractively (parts 1–5). The core platform never depends on AI.

---

## 4. User journeys

1. **First visit** → Dashboard shows "Start here: Stage 1 · Lesson 1", the full journey map, 0 % progress.
2. **Daily study** → Dashboard → *Continue learning* → lesson → watch embedded video in-page →
   read concept ladder → exercise → quiz → mastery updated → *Recommended next lesson*.
3. **Revision** → Flashcards due today (SM-2) → Revision mode (mixed questions, weakest topics first).
4. **Project work** → Projects → capstone spec → milestones checked off with evidence links → rubric self-assessment → submission.
5. **Interview prep** → Assessments → Interview mode by track (Python, SQL, ML/DL, LLM, RAG, Agents, System design).
6. **Tutor** → Tutor page → Forge progress → (after reveal) ask questions grounded in course content, with citations.
7. **Analytics** → Progress page: stage/module completion, mastery heatmap, hours, streak, weak areas.

---

## 5. Development phases

| Phase | Scope | Exit criteria |
|---|---|---|
| 1 Planning | this document, schema, content format, coverage check | coverage check passes for all 23 domains |
| 2 Core platform | API + DB + seed; dashboard, sidebar, curriculum, paths, lessons, progress, resource library | app runs; lesson progress persists |
| 3 Educational features | quizzes (all kinds), exercises, flashcards + SM-2, revision mode, interview mode, mastery | tests for grading, mastery, SRS |
| 4 Projects | catalog, workspace, milestones, rubric, submission tracking | |
| 5 AI features | Tutor Forge runner, tutor UI, recommendations, AI-assisted revision | forge tests verified via UI |
| 6 Production readiness | auth (JWT, hashed passwords), security review, tests, responsive/a11y, deployment docs | |

---

## 6. Technology stack & justification

The prompt asks for a mix of tools so the learner gets hands-on with the real AI-engineering stack.

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js 15 + React 19 + TypeScript** | industry standard; SSR for fast lesson pages; type safety |
| Styling | **Tailwind CSS v4** + CSS variables | design tokens, excellent dark mode, no runtime cost |
| UI | Hand-built accessible components (Radix-style patterns), `lucide-react` icons | no heavy kit; Linear/Notion-like minimalism |
| Markdown | `react-markdown` + `remark-gfm` + `remark-math`/`rehype-katex` + `rehype-highlight` | maths and beautiful code blocks |
| Charts | **Recharts** | simple, composable progress charts |
| Backend | **FastAPI + Pydantic v2** | the dominant Python API framework for AI services — the learner studies it in M21 |
| ORM | **SQLAlchemy 2.x** | portable SQLite ↔ PostgreSQL; taught in M04/M21 |
| Database | **SQLite** (dev) / **PostgreSQL** (prod) | zero-install locally; Postgres in deployment |
| Auth | JWT (PyJWT) + bcrypt-hashed passwords; `AUTH_MODE=local` single learner by default | |
| Content | YAML + Markdown in git | reviewable, versioned, diff-friendly |
| Testing | pytest (API, coverage, forge) · TypeScript typecheck · Next build | |
| Deployment | Docker Compose (web + api + postgres), docs for Render/Fly/Vercel | taught in M24 |
