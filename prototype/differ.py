"""
Compares two symbol maps (old vs new) and classifies each symbol.

This is the "sync" logic: it's what lets the agent regenerate docs only
for what actually changed, instead of re-running the LLM over the whole
file on every commit.
"""
from dataclasses import dataclass

from prototype.symbol_extractor import Symbol


@dataclass
class DiffResult:
    added: list[Symbol]
    removed: list[str]          # just names — the old symbol is gone, nothing to show
    modified: list[tuple[Symbol, Symbol]]  # (old, new)
    unchanged: list[Symbol]


def diff_symbols(old: dict[str, Symbol], new: dict[str, Symbol]) -> DiffResult:
    old_names = set(old.keys())
    new_names = set(new.keys())

    added = [new[name] for name in sorted(new_names - old_names)]
    removed = sorted(old_names - new_names)

    modified = []
    unchanged = []
    for name in sorted(old_names & new_names):
        if old[name].signature_hash != new[name].signature_hash:
            modified.append((old[name], new[name]))
        else:
            unchanged.append(new[name])

    return DiffResult(added=added, removed=removed, modified=modified, unchanged=unchanged)
