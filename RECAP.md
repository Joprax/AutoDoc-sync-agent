# AI Documentation Generator & Sync Agent — Recap

## The idea
A follow-up portfolio project to the PR Review Automation Agent. Instead of
reviewing code quality, this agent watches a repo, detects when code
*actually* changes (not just any commit — specifically signatures,
params, new/removed functions), and uses an LLM to generate or update
documentation for exactly what changed. The "sync" part is the
differentiator: it tracks doc-to-code drift over time instead of
blindly regenerating everything on every push.

## Why this approach
The riskiest unknown wasn't "can I stand up a FastAPI + Celery service" —
you already proved that with the PR review agent. The unknown was
"can I reliably detect what changed in code and describe it well with an
LLM." So the plan was: scaffold the API skeleton first (fast, known
territory), then prove the parse → diff → generate loop works as a
standalone script *before* wiring it into the real pipeline.

## What's built so far

### 1. API scaffold (`app/`)
Full FastAPI + Celery + Redis + Postgres skeleton, same pattern as your
PR review agent:
- `main.py` — FastAPI app, two routers registered
- `db/models.py` — `Repo`, `Symbol` (tracks a signature hash per
  function/class), `SyncRun` (history per push)
- `api/routes/webhook.py` — GitHub webhook receiver, verifies HMAC
  signature, queues a Celery task, returns immediately
- `api/routes/repos.py` — read endpoints for a future dashboard
- `workers/tasks.py` — `process_push_event`, currently a stub with 5
  TODOs marking exactly where the real logic plugs in
- `docker-compose.yml` — local Postgres + Redis only (app runs directly)

**Status:** runs, compiles clean, not yet connected to real GitHub data.

### 2. Parse + diff prototype (`prototype/`) — proven working
Standalone, no API/DB/Celery needed:
- `symbol_extractor.py` — parses a Python file's AST, extracts every
  function/method/class into a `Symbol` with a structural signature hash
  (deliberately ignores docstrings/comments — only the *contract* matters)
- `differ.py` — compares two symbol maps, classifies each as
  added / removed / modified / unchanged
- `fixtures/before.py` + `fixtures/after.py` — realistic test case
- `run_prototype.py` — CLI script tying it together

**Verified result:** ran against the fixtures and correctly identified
1 added, 2 modified, 1 removed, 2 unchanged symbols — proving the core
"only touch what actually changed" logic works.

### 3. Doc generation (`prototype/doc_generator.py`) — wired, needs testing
- Calls Gemini (`google-genai` SDK) with a prompt built from a symbol's
  signature + existing docstring
- `run_prototype.py` now feeds added/modified symbols into this and
  prints the generated docstrings
- Currently blocked on you rotating your Gemini API key and re-running
  with `.env` loading fixed (see above)

## What's NOT built yet
1. **Real git integration** — currently uses two static fixture files;
   needs to pull an actual `git diff` / GitHub API response for a real
   commit instead
2. **Wiring into `process_push_event`** — the Celery task stub has TODOs
   marking exactly where parse → diff → generate need to be called for
   real
3. **Write-back** — nothing commits generated docs anywhere yet (target:
   commit to a docs branch + open a PR, same review-friendly pattern as
   the PR review agent)
4. **JS/TS support** — Python-only for now by design (MVP scope)

## Suggested order from here
1. Confirm doc generation works end-to-end with a fresh key
2. Real git diff integration (replace the fixture files)
3. Wire the proven prototype logic into `process_push_event`
4. Write-back to a docs branch + PR
5. Dashboard (repo list, drift view, manual regenerate)
