# Doc Sync Agent — API Scaffold

Skeleton for the AI Documentation Generator & Sync Agent. The parse/diff/generate
logic (the actual "brains") isn't built yet — this scaffold gives you a running
webhook -> queue -> DB pipeline to build that logic into.

## What's here

```
app/
  main.py              FastAPI app + route registration
  core/config.py        Settings (env vars)
  db/base.py             SQLAlchemy engine/session
  db/models.py            Repo, Symbol, SyncRun tables
  schemas.py               Pydantic response models
  api/routes/webhook.py     POST /webhook/github — verifies signature, queues a task
  api/routes/repos.py        GET endpoints for the dashboard
  workers/celery_app.py      Celery config (Redis broker/backend)
  workers/tasks.py            process_push_event — currently a stub with TODOs
```

## What's NOT here yet (on purpose)
- AST/tree-sitter parsing of changed files
- Signature-hash diffing against stored Symbol rows
- Gemini call to generate doc content
- Writing docs back to the repo (branch + PR)

These all plug into the TODOs in `app/workers/tasks.py::process_push_event`.

## Local setup

1. Start Postgres + Redis:
   ```
   docker compose up -d
   ```
   This only starts the two infra containers — nothing destructive, safe to run repeatedly.

2. Create a virtualenv and install deps:
   ```
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in `GITHUB_WEBHOOK_SECRET` and `GEMINI_API_KEY`.

4. Create the tables (no migration tool wired up yet — this is a quick way to
   get started; swap in Alembic once the schema stabilizes):
   ```
   python -c "from app.db.base import Base, engine; from app.db import models; Base.metadata.create_all(engine)"
   ```

5. Run the API:
   ```
   uvicorn app.main:app --reload
   ```

6. Run a worker (separate terminal):
   ```
   celery -A app.workers.celery_app worker --loglevel=info
   ```

7. Point a GitHub webhook (push events) at `POST /webhook/github`, with the
   same secret as `GITHUB_WEBHOOK_SECRET`. For local testing before you have
   a public URL, use `ngrok http 8000` or just call the endpoint manually
   with a sample push payload.

## Next steps
See the project plan — next up is proving out the parse -> diff -> generate
loop as a standalone script before wiring it into `process_push_event`.
