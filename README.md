# doc-sync-agent

**Automated documentation that stays in sync with your code — reviewed by a human before it ever lands.**

Every push to a watched repository is diffed at the *symbol level* (functions, classes — not raw text lines). If a signature actually changed, the agent generates documentation for it with Gemini, opens a pull request with the update, and waits for a human to review and merge. If nothing meaningful changed, it does nothing — no noise, no docs PRs for whitespace or comment edits.

---

## How it works

```
GitHub push
    │
    ▼
Webhook → doc-sync-api (FastAPI)
    │
    ▼
Clone/update the repo locally
    │
    ▼
Diff symbols between before/after commit
    │
    ▼
Changed signatures found? ──No──▶ done, nothing to do
    │
   Yes
    │
    ▼
Generate docs for changed symbols (Gemini)
    │
    ▼
Branch → commit docs → push → open PR
    │
    ▼
Human reviews & merges
```

## Live components

| Component | What it does | Hosted on |
|---|---|---|
| **doc-sync-api** | Receives GitHub webhooks, verifies signatures, runs the pipeline | Render |
| **doc-sync-db** | Stores registered repos, sync history, documented symbols | Render (Postgres) |
| **dashboard** | Read-only view of watched repos, sync history, and generated docs | Vercel |

## Try it

1. **Register a repo** (one-time, per repo):
   ```bash
   python -m scripts.seed_repo owner/repo-name
   ```
2. **Push a commit** that changes a function or class signature.
3. Watch the [dashboard](#) — a new sync entry appears, and a PR shows up in the repo with the generated docs attached.

## Tech stack

- **FastAPI** — webhook receiver and dashboard API
- **PostgreSQL** — persisted repo registry, sync history, and generated docs
- **SQLAlchemy** — ORM layer
- **Google Gemini** — documentation generation from function/class signatures
- **GitHub REST API** — opening pull requests programmatically
- **Render** — API + database hosting
- **Vercel** — dashboard hosting

## What it deliberately doesn't do

- **Doesn't commit to `main` directly.** Every generated doc goes through a PR — a human always has the final say.
- **Doesn't regenerate docs for unchanged code.** Diffing happens at the symbol level, so a formatting pass or comment tweak doesn't trigger a doc rewrite.
- **Doesn't run a background job queue in production.**