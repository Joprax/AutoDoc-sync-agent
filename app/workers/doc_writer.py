"""
Turns generated doc content into markdown files, one per source file that
had changes. Writing separate doc pages (rather than rewriting docstrings
inside the source files themselves) keeps this safe and easy to review in
a PR diff — no risk of an AST rewrite subtly corrupting someone's code.
"""
import os


def render_markdown_for_file(source_file_path: str, symbols_with_docs: list[tuple]) -> str:
    """symbols_with_docs is a list of (Symbol, doc_text) tuples belonging to
    one source file. Returns the full markdown content for that file's doc page."""
    lines = [f"# `{source_file_path}`", ""]
    for symbol, doc_text in symbols_with_docs:
        lines.append(f"## `{symbol.qualified_name}`")
        lines.append("")
        lines.append(f"```python\n{symbol.signature}\n```")
        lines.append("")
        lines.append(doc_text or "*(no description generated)*")
        lines.append("")
    return "\n".join(lines)


def write_doc_pages(
    local_repo_path: str,
    docs_output_path: str,
    changed: list[tuple],          # (file_path, Symbol)
    generated_docs: dict[str, str], # qualified_name -> doc text
) -> list[str]:
    """Writes one markdown file per changed source file under
    <local_repo_path>/<docs_output_path>/<mirrored source path>.md.
    Returns the list of relative paths written, so the caller knows what to
    `git add`."""
    by_file: dict[str, list[tuple]] = {}
    for file_path, symbol in changed:
        by_file.setdefault(file_path, []).append((symbol, generated_docs.get(symbol.qualified_name)))

    written = []
    for source_file_path, symbols_with_docs in by_file.items():
        # e.g. "app/workers/tasks.py" -> "docs/app/workers/tasks.py.md"
        doc_relative_path = os.path.join(docs_output_path, source_file_path + ".md")
        doc_absolute_path = os.path.join(local_repo_path, doc_relative_path)

        os.makedirs(os.path.dirname(doc_absolute_path), exist_ok=True)
        content = render_markdown_for_file(source_file_path, symbols_with_docs)
        with open(doc_absolute_path, "w", encoding="utf-8") as f:
            f.write(content)

        written.append(doc_relative_path)

    return written
