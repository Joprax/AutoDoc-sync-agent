# `app/workers/git_ops.py`

## `_run_git`

```python
def _run_git(*args, cwd: str | None) -> str
```

Execute a git command with the given arguments and return its output.

## `ensure_local_clone`

```python
def ensure_local_clone(clone_url: str, repo_full_name: str, base_dir: str) -> str
```

Returns the local path to an up-to-date, full clone of a repository. Clones the repository fresh if it does not exist locally, or fetches all references on subsequent calls to ensure required commit histories are available for diffing.
