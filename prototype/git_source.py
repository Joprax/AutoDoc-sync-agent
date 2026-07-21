"""
Replaces the hardcoded fixture files with real git history. Uses `git`
directly via subprocess rather than a library like GitPython — this is a
handful of read-only commands, not worth adding a dependency for.

Two git refs in, two dicts of {file_path: source_text} out. A file that's
None means it didn't exist at that ref (i.e. it was added or removed
between the two commits, not modified).
"""
import subprocess


def _run_git(repo_path: str, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo_path, *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def list_changed_python_files(repo_path: str, old_ref: str, new_ref: str) -> list[str]:
    """Returns repo-relative paths of .py files that differ between the two refs."""
    output = _run_git(repo_path, "diff", "--name-only", old_ref, new_ref, "--", "*.py")
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_file_at_ref(repo_path: str, ref: str, file_path: str) -> str | None:
    """Returns the file's content at a given commit, or None if it doesn't
    exist there (covers both 'added since old_ref' and 'removed by new_ref')."""
    result = subprocess.run(
        ["git", "-C", repo_path, "show", f"{ref}:{file_path}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # git show fails with a non-zero exit if the path doesn't exist at that ref —
        # that's an expected case here, not an error worth raising.
        return None
    return result.stdout


def get_changed_file_versions(
    repo_path: str, old_ref: str, new_ref: str
) -> dict[str, tuple[str | None, str | None]]:
    """Returns {file_path: (old_source_or_None, new_source_or_None)} for every
    changed .py file between old_ref and new_ref."""
    changed_files = list_changed_python_files(repo_path, old_ref, new_ref)
    versions = {}
    for file_path in changed_files:
        old_source = get_file_at_ref(repo_path, old_ref, file_path)
        new_source = get_file_at_ref(repo_path, new_ref, file_path)
        versions[file_path] = (old_source, new_source)
    return versions
