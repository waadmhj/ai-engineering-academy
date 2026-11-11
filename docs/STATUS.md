# Status — end of session 1 (2026-11-10)

## Verified working

| Area | State | How it was verified |
|---|---|---|
| Curriculum: 6 stages, 28 modules, 182 lessons | ✅ | Seeded from YAML, schema-validated with cross-reference checks |
| Roadmap coverage | ✅ 331/331 topics | `scripts/check_coverage.py` (also a pytest) |
| Resource library: 238 real resources (55 videos, 20 books, 74 docs, 20 courses, 8 interactive, 9 articles, 52 papers with plain-language summaries) | ✅ 231/238 links verified | `scripts/verify_resources.py`. YouTube IDs checked via oEmbed. The other 7 failed only because of this machine's network (SSL interception on stanford.edu, connection resets); re-run elsewhere |
| Fully authored lessons with the full concept ladder, diagram, maths, code, exercise and solution, 7-question assessment and flashcards | ✅ 5 lessons: `py-01`, `ma-02`, `sm-05`, `emb-01`, `rag-01` | Rendered and visually checked |
| Outline lessons (177): objectives, required/supplementary resources, self-check | ✅ | Clearly labelled "Guided outline" in the UI; cannot be marked mastered |
| Dashboard, paths, curriculum, module and lesson pages, resource library | ✅ | Production build plus headless screenshots |
| Progress tracking (5 statuses, server-enforced evidence rules), mastery score, study time, streaks | ✅ | API tests |
| Quizzes (MCQ, multi-select, short, technical, practical, scenario) with active recall and self-grading | ✅ | API tests |
| Exercises with hints, reference solution after submission, advanced challenge | ✅ | API tests |
| Flashcards with SM-2 spaced repetition | ✅ | Unit tests |
| Revision mode (weakest first, auto-flags lessons for revision) and interview mode (35 questions, 7 tracks) | ✅ | API tests |
| Projects: 8 mini, 9 module, 12 capstones and 1 portfolio project, each capstone with the 16 required sections, milestones with evidence, ADRs and a weighted rubric | ✅ | API tests (submission rules) |
| Tutor Forge: 7 workshops, verification via pytest, locked tutor, reveal, grounded tutor with citations, optional LLM | ✅ | End-to-end test with the reference solutions |
| Annotations: text highlights (5 colours), sticky notes (drag, pin, collapse), pen/marker ink with eraser, undo, Notebook page, pinned notes on the dashboard | ✅ | API tests (`test_annotations.py`) and a scripted headless-browser run (light, dark, 390px mobile) |
| JWT auth mode (register/login, bcrypt) | ✅ implemented | Not covered by automated tests yet |
| Dark mode, responsive layout, keyboard search (Ctrl K) | ✅ | Screenshots (desktop). Mobile layout implemented but not screenshot-tested |

## Not done yet (next sessions)

1. **Author the remaining 177 lessons** to the same standard as the five flagship lessons. The schema enforces the full structure, so each one is a YAML file in `content/lessons/<id>.yaml`. Suggested order: the rest of Stage 1 (the learner starts there), then the lessons that carry workshops (`py-04`, `da-04`, `ml-05`, `api-08`, `pe-03`, `rag-04`).
2. **In-browser code execution** (e.g. Pyodide) so exercises are auto-checked, not just self-reported.
3. **Docker deployment**: `docker-compose.yml` and both Dockerfiles are written but not built here, because Docker isn't installed on this machine.
4. **Database migrations** (Alembic). The schema is currently created with `create_all`.
5. **Frontend tests** (Playwright) and API tests for JWT mode.
6. **AI-powered revision/recommendations**: today recommendations are rule-based (prerequisites + mastery). LLM-generated practice exams can be layered on through the learner's tutor.
7. Coursera's catalog connector failed to authenticate this session, so course entries were added by hand from known URLs and link-checked instead.

## Known limitations

* Some documentation sites block iframe embedding. "Read in platform" shows a notice and an "Open original" link.
* Exercise completion for full lessons is self-reported (with the code saved). Workshops are verified automatically.
* Pen and marker drawings are positioned relative to the nearest lesson section. If text reflows (window much narrower or wider), a drawing stays near its section but may no longer line up exactly with the words it marked. Highlights don't have this problem.
* Text highlights use the CSS Custom Highlight API (Chrome/Edge 105+, Safari 17.2+, Firefox 140+). In older browsers the highlighter is disabled with a message; notes and drawing still work.
