# Deployment

## Docker Compose (PostgreSQL + API + web)

```bash
cp api/.env.example .env      # set POSTGRES_PASSWORD, JWT_SECRET, AUTH_MODE
docker compose up --build     # http://localhost:3000
```

## Production checklist

* `AUTH_MODE=jwt` for anything reachable by more than one person, plus a long random `JWT_SECRET` (e.g. `python -c "import secrets;print(secrets.token_urlsafe(48))"`).
* In jwt mode, workshop verification and the tutor are **disabled** because they execute learner code. Enable them only with a sandbox (container per user, no network, CPU/memory limits) and `FORGE_ALLOW_EXEC=1`.
* PostgreSQL via `DATABASE_URL=postgresql+psycopg://…`. Content tables are re-seeded from `content/` on an empty database; run `python -m app.content.loader` after content changes. Learner data is never touched by seeding.
* Set `CORS_ORIGINS` to your web origin and `API_URL` for the Next.js proxy.
* Keep API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) in a secret manager, never in the repository.
* Run CI on every push: `pytest`, `scripts/check_coverage.py`, `npx tsc --noEmit`, `npm run lint`, `npm run build`. Run `scripts/verify_resources.py` on a weekly schedule to catch dead links.

## Netlify (frontend) + Render (API) + Neon (database)

Netlify cannot run the Python API (it needs a long-running server and a persistent database), so it hosts only `web/`.

1. **Database (Neon):** create a project and copy the connection string. Change `postgresql://` to `postgresql+psycopg://`.
2. **API (Render → New Web Service → Docker):** set the repository root as the build context and `api/Dockerfile` as the Dockerfile. Set these environment variables:
   * `DATABASE_URL`: the URL from step 1
   * `AUTH_MODE=jwt`
   * `JWT_SECRET`: a long random string
   * `CORS_ORIGINS`: `https://<site>.netlify.app`
   * `CONTENT_DIR=/app/content`, `ROADMAP_FILE=/app/content.md`, `FORGE_DIR=/app/forge`

   Check that `https://<api>.onrender.com/api/curriculum` returns JSON.
3. **Web (Netlify → Import from Git):** `netlify.toml` already sets the base to `web/`. Add the environment variable `API_URL=https://<api>.onrender.com`, then deploy. If you change `API_URL` later, redeploy, because it is read at build time.

## Hosting options

* **Web:** Vercel or any Node host (`npm run build && npx next start`).
* **API:** Render, Fly.io, Railway, AWS ECS/Fargate or Cloud Run, using `api/Dockerfile` with the repository root as build context.
* **Database:** managed PostgreSQL (Neon, Supabase, RDS, Cloud SQL).
