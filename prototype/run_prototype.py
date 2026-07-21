"""
Standalone prototype: no FastAPI, no Celery, no DB — just proving the core
loop works: parse two versions of a file -> diff symbols -> report what
actually needs new/updated docs.

Run from the doc-sync-agent/ directory:
    python -m prototype.run_prototype
"""
import os
from pathlib import Path

from dotenv import load_dotenv

from prototype.differ import diff_symbols
from prototype.symbol_extractor import extract_symbols

load_dotenv()  # standalone script — nothing else loads .env for us here

FIXTURES = Path(__file__).parent / "fixtures"


def main():
    old_source = (FIXTURES / "before.py").read_text()
    new_source = (FIXTURES / "after.py").read_text()

    old_symbols = extract_symbols(old_source)
    new_symbols = extract_symbols(new_source)

    result = diff_symbols(old_symbols, new_symbols)

    print(f"Unchanged ({len(result.unchanged)}) — skipped, no doc work needed:")
    for sym in result.unchanged:
        print(f"    {sym.qualified_name}")

    print(f"\nAdded ({len(result.added)}) — needs new docs:")
    for sym in result.added:
        print(f"    {sym.qualified_name}  {sym.signature}")

    print(f"\nModified ({len(result.modified)}) — needs updated docs:")
    for old_sym, new_sym in result.modified:
        print(f"    {new_sym.qualified_name}")
        print(f"        before: {old_sym.signature}")
        print(f"        after:  {new_sym.signature}")

    print(f"\nRemoved ({len(result.removed)}) — docs should be deleted/flagged:")
    for name in result.removed:
        print(f"    {name}")

    changed_symbols = result.added + [new_sym for _, new_sym in result.modified]
    print(f"\n{len(changed_symbols)} symbol(s) would be sent to the LLM for doc generation.")

    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "\nGEMINI_API_KEY not set — skipping actual generation.\n"
            "Export it and re-run to see real generated docstrings:\n"
            "    export GEMINI_API_KEY=your_key_here"
        )
        return

    from prototype.doc_generator import generate_docs_for_symbols

    print("\nGenerating docs...\n")
    generated = generate_docs_for_symbols(changed_symbols)
    for qualified_name, doc_text in generated.items():
        print(f"--- {qualified_name} ---")
        print(doc_text)
        print()


if __name__ == "__main__":
    main()