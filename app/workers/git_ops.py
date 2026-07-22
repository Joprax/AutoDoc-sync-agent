"""
Gets a local, up-to-date clone of a webhook's repo on disk. The existing
git-based diff logic (git_source.py, built for the local prototype) works
against a local repo path — this is what makes that logic reusable here
instead of reimplementing diffing against the GitHub REST API directly.
"""
import os
import subprocess


def run_git(*args: str, cwd: str | None = None) -> str:
    """Runs a git command and returns its stdout. Raises RuntimeError with
    stderr on failure. Public — shared by git_ops.py (cloning/fetching) and
    github_pr.py (branching/committing/pushing for write-back)."""
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def ensure_local_clone(clone_url: str, repo_full_name: str, base_dir: str) -> str:
    """Returns the local path to an up-to-date clone of the repo: clones it
    fresh the first time this repo is seen, and fetches all refs on every
    call after that so old_ref/new_ref commit SHAs from the webhook are
    guaranteed to exist locally.

    Note: does a full (non-shallow) clone on purpose — a shallow clone might
    not have the "before" commit's history available locally, which would
    make git diff between old_ref and new_ref fail."""
    local_path = os.path.join(base_dir, repo_full_name.replace("/", "__"))

    if not os.path.isdir(os.path.join(local_path, ".git")):
        os.makedirs(base_dir, exist_ok=True)
        run_git("clone", clone_url, local_path)
    else:
        run_git("fetch", "--all", cwd=local_path)

    return local_path