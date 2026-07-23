# AI Documentation Generator & Sync Agent

An agent that watches a GitHub repo, detects when a function or class
**signature** actually changes (not just any commit), generates documentation
for exactly what changed with an LLM, and opens a pull request — so nothing
gets written to `main` without a human reviewing it first.

Push code → the agent diffs it at the symbol level → generates docs for what
changed → opens a PR with the results.

## Why symbol-level diffing

Most doc tools either regenerate everything on every commit (slow, noisy,
expensive) or rely on someone remembering to update docs by hand (they
don't). This agent parses each changed file's AST, hashes every function
and class signature, and compares that hash against what it saw last time.
A commit that only touches internals, comments, or formatting produces
**zero** LLM calls. Only a real signature change — a new parameter, a
different return type, a new/removed function — triggers doc generation.

## How it works

```
GitHub push
    │
    ▼
Webhook → FastAPI (verifies signature, queues a task)
    │
    ▼
Celery worker
    │
    ├─ clone/update the repo locally
    ├─ diff old commit vs new commit, symbol by symbol (Python AST)
    ├─ generate docs for changed symbols only (Gemini)
    ├─ persist results to Postgres
    └─ commit generated docs on a new branch → push → open a PR
```

Every run is logged (status, symbols changed, PR link, any error) and
visible in the dashboard.

## Stack

- **API / worker**: FastAPI, Celery, Redis, PostgreSQL (SQLAlchemy)
- **LLM**: Gemini
- **Dashboard**: Next.js (App Router), server-rendered against the API
- **Parsing**: Python's built-in `ast` module — no external parser dependency

## Project structure

```
app/                  FastAPI app, DB models, Celery task, GitHub write-back
prototype/            Core parse/diff/generate logic (standalone, testable
                       without any web framework — reused as-is by app/)
scripts/               One-off admin scripts (register a repo, manual test trigger)
dashboard/             Next.js frontend
```

## Running it locally

**1. Start infrastructure**
```bash
docker compose up -d
```

**2. Set up the backend**
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # then fill in GEMINI_API_KEY, GITHUB_WEBHOOK_SECRET,
                               # and GITHUB_APP_TOKEN (see below)
```

**3. Create the database tables and register a repo**
```bash
python -c "from app.db.base import Base, engine; from app.db import models; Base.metadata.create_all(engine)"
python -m scripts.seed_repo owner/repo-name
```

**4. Run the API and worker** (separate terminals)
```bash
uvicorn app.main:app --reload
celery -A app.workers.celery_app worker --loglevel=info --pool=solo   # --pool=solo needed on Windows
```

**5. Run the dashboard**
```bash
cd dashboard
npm install
cp .env.example .env.local
npm run dev
```
Open `http://localhost:3000`.

**6. Point a real webhook at it**

Locally, your machine isn't publicly reachable, so tunnel it:
```bash
ngrok http 8000
```
Then on GitHub → your repo → Settings → Webhooks → Add webhook:
- Payload URL: `https://<your-ngrok-url>/webhook/github`
- Content type: `application/json`
- Secret: same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
- Events: just the `push` event

Push a commit that changes a function signature and watch it flow through.

## GitHub token setup

`GITHUB_APP_TOKEN` needs write access to open PRs. Use a **fine-grained
personal access token**, scoped to only the repo you're watching, with:
- Contents: Read and write
- Pull requests: Read and write

## Testing without a live webhook

```bash
python -m scripts.test_webhook owner/repo-name
```
Resolves your local repo's last two commits into real SHAs and runs the
full pipeline directly — no ngrok, no GitHub webhook needed, useful for
quick iteration.

## Design notes

- **Docs are separate markdown pages, not rewritten docstrings.** Editing
  source files via AST rewriting risks subtly corrupting code; generated
  docs land in mirrored `.md` files under `docs_output_path` instead,
  reviewable in a clean PR diff.
- **Never pushes to the default branch directly.** Every write-back goes
  through a `docs-sync/<sha>` branch and a PR — a human always reviews
  before anything merges.
- **The agent's own PR-branch pushes don't re-trigger itself** — the
  webhook handler only reacts to pushes on the repo's configured default
  branch.
- **Idempotent by design.** Retries and webhook redeliveries reuse or
  cleanly replace branches/PRs rather than erroring on "already exists."

## Status

Core pipeline (trigger → parse → diff → generate → write-back → PR) and
the dashboard are complete and tested end-to-end against a real repo.
Not yet done: deployment (currently local-only), JS/TS support (Python
only for now).
