"""
Turns a set of written doc files into a real GitHub PR: branch off the
pushed commit, commit the doc changes, push the branch, open a PR. Nothing
ever gets pushed to the repo's default branch directly — same
review-friendly pattern as the PR review agent, so generated docs always
go through a human review step before landing on main.

Split into separate steps (rather than one do-everything function) because
the caller needs to write the doc files to disk *between* checking out the
branch and committing — checking out a different commit while there are
already-written, uncommitted files in the working tree is exactly what
broke this originally (git correctly refuses, to avoid silently
overwriting them).
"""
import subprocess

import requests

from app.workers.git_ops import run_git


def checkout_new_branch(local_repo_path: str, branch_name: str, base_sha: str) -> None:
    """Checks out base_sha, then creates branch_name from it. Must run
    BEFORE any files are written into the working tree — git refuses to
    switch commits if doing so would overwrite uncommitted changes."""
    run_git("checkout", base_sha, cwd=local_repo_path)

    # If a previous run already created this branch (e.g. a retry after a
    # failure), delete it first so this stays idempotent instead of failing
    # with "branch already exists". Failure here is fine (branch may not
    # exist yet) — deliberately not using run_git, which would raise.
    subprocess.run(
        ["git", "-C", local_repo_path, "branch", "-D", branch_name],
        capture_output=True, text=True,
    )

    run_git("checkout", "-b", branch_name, cwd=local_repo_path)


def commit_files(local_repo_path: str, relative_paths: list[str], commit_message: str) -> None:
    """Stages and commits the given files. Call this only after the branch
    is checked out AND the files have actually been written to disk."""
    run_git("add", *relative_paths, cwd=local_repo_path)
    run_git("commit", "-m", commit_message, cwd=local_repo_path)


def push_branch(local_repo_path: str, repo_full_name: str, branch_name: str, github_token: str) -> None:
    """Pushes the branch using a token-authenticated URL, rather than
    relying on any locally configured git credentials — this runs on a
    server/worker, not a developer's machine, so it can't assume SSH keys
    or a stored credential helper are set up. --force since the branch may
    already exist on the remote from a previous run of the same commit."""
    auth_url = f"https://x-access-token:{github_token}@github.com/{repo_full_name}.git"
    run_git("push", "--force", auth_url, branch_name, cwd=local_repo_path)


def open_pull_request(
    repo_full_name: str,
    branch_name: str,
    base_branch: str,
    title: str,
    body: str,
    github_token: str,
) -> str:
    """Opens a PR via the GitHub REST API and returns its URL. If a PR for
    this branch already exists (e.g. a retry), GitHub returns a 422 —
    in that case, look up and return the existing PR's URL instead of
    treating it as a failure."""
    response = requests.post(
        f"https://api.github.com/repos/{repo_full_name}/pulls",
        headers={
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        },
        json={"title": title, "head": branch_name, "base": base_branch, "body": body},
        timeout=30,
    )

    if response.status_code == 422:
        existing = requests.get(
            f"https://api.github.com/repos/{repo_full_name}/pulls",
            headers={"Authorization": f"Bearer {github_token}"},
            params={"head": f"{repo_full_name.split('/')[0]}:{branch_name}", "state": "open"},
            timeout=30,
        )
        existing.raise_for_status()
        results = existing.json()
        if results:
            return results[0]["html_url"]

    response.raise_for_status()
    return response.json()["html_url"]


def write_back_docs(
    local_repo_path: str,
    repo_full_name: str,
    base_branch: str,
    base_sha: str,
    symbols_changed: int,
    github_token: str,
    write_files_callback,
) -> str:
    """Full write-back flow, in the order that actually works:
    1. Checkout the branch (working tree is still clean at this point)
    2. write_files_callback() — caller writes doc files now, tree gets dirty
    3. Commit those files
    4. Push, open PR

    write_files_callback must return the list of relative paths it wrote,
    so they can be staged in the commit."""
    branch_name = f"docs-sync/{base_sha[:7]}"
    commit_message = f"docs: sync generated documentation for {symbols_changed} symbol(s)"

    checkout_new_branch(local_repo_path, branch_name, base_sha)
    relative_paths = write_files_callback()
    commit_files(local_repo_path, relative_paths, commit_message)
    push_branch(local_repo_path, repo_full_name, branch_name, github_token)

    return open_pull_request(
        repo_full_name=repo_full_name,
        branch_name=branch_name,
        base_branch=base_branch,
        title=f"Sync generated docs for {symbols_changed} changed symbol(s)",
        body=(
            "Auto-generated by the Documentation Generator & Sync Agent.\n\n"
            f"This PR updates documentation for {symbols_changed} symbol(s) whose "
            f"signatures changed in commit `{base_sha}`. Please review before merging."
        ),
        github_token=github_token,
    )
