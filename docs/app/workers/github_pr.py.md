# `app/workers/github_pr.py`

## `commit_files`

```python
def commit_files(local_repo_path: str, relative_paths: list[str], commit_message: str) -> None
```

Stages and commits the specified files in a local repository. Must be called after the appropriate branch is checked out and the files are written to disk.

## `write_back_docs`

```python
def write_back_docs(local_repo_path: str, repo_full_name: str, base_branch: str, base_sha: str, symbols_changed: int, github_token: str, write_files_callback) -> str
```

Executes the complete write-back workflow by checking out the specified branch, invoking the callback to generate documentation files, and committing and pushing the changes to open a pull request. The callback must return the list of relative file paths written so they can be staged for the commit.
