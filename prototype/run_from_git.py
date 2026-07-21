"""
Same pipeline as run_prototype.py, but pulling real file versions from an
actual git repo instead of the static before.py/after.py fixtures.

Usage:
    python -m prototype.run_from_git <repo_path> <old_ref> <new_ref>

Example (against your own PR review agent repo, comparing the last two commits):
    python -m prototype.run_from_git ../pr-review-agent HEAD~1 HEAD
"""
import os
import sys

from dotenv import load_dotenv

from prototype.differ import diff_symbols
from prototype.git_source import get_changed_file_versions
from prototype.symbol_extractor import extract_symbols

load_dotenv()


def main():
    if len(sys.argv) != 4:
        print("Usage: python -m prototype.run_from_git <repo_path> <old_ref> <new_ref>")
        sys.exit(1)

    repo_path, old_ref, new_ref = sys.argv[1], sys.argv[2], sys.argv[3]

    file_versions = get_changed_file_versions(repo_path, old_ref, new_ref)

    if not file_versions:
        print(f"No changed .py files between {old_ref} and {new_ref}.")
        return

    all_changed_symbols = []

    for file_path, (old_source, new_source) in file_versions.items():
        print(f"\n=== {file_path} ===")

        # File didn't exist before this range — every symbol in it is new.
        old_symbols = extract_symbols(old_source) if old_source is not None else {}
        # File was deleted by new_ref — nothing to generate, everything's gone.
        new_symbols = extract_symbols(new_source) if new_source is not None else {}

        result = diff_symbols(old_symbols, new_symbols)

        print(f"Added: {len(result.added)}, Modified: {len(result.modified)}, "
              f"Removed: {len(result.removed)}, Unchanged: {len(result.unchanged)}")

        for sym in result.added:
            print(f"  + {sym.qualified_name}  {sym.signature}")
        for old_sym, new_sym in result.modified:
            print(f"  ~ {new_sym.qualified_name}")
            print(f"      before: {old_sym.signature}")
            print(f"      after:  {new_sym.signature}")
        for name in result.removed:
            print(f"  - {name}")

        all_changed_symbols.extend(result.added + [new_sym for _, new_sym in result.modified])

    print(f"\n{len(all_changed_symbols)} symbol(s) total would be sent to the LLM for doc generation.")

    if not all_changed_symbols:
        return

    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "\nGEMINI_API_KEY not set — skipping actual generation.\n"
            "Export it and re-run to see real generated docstrings."
        )
        return

    from prototype.doc_generator import generate_docs_for_symbols

    print("\nGenerating docs...\n")
    generated = generate_docs_for_symbols(all_changed_symbols)
    for qualified_name, doc_text in generated.items():
        print(f"--- {qualified_name} ---")
        print(doc_text)
        print()


if __name__ == "__main__":
    main()
