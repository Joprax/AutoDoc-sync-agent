"""
Parses a Python source file into a flat map of "symbols" — functions,
methods, and classes — each with a structural signature hash.

The hash deliberately excludes the docstring/body: it's built only from
things that change the *contract* of the symbol (params, defaults,
annotations, decorators, base classes). That's the whole point — a
docstring or comment edit shouldn't trigger "this needs new docs", but
adding a parameter should.
"""
import ast
import hashlib
from dataclasses import dataclass, field


@dataclass
class Symbol:
    qualified_name: str      # e.g. "PRReviewer.run" or "review_pull_request"
    kind: str                 # "function" | "async_function" | "class"
    lineno: int
    signature: str            # human-readable signature, used for the doc prompt later
    signature_hash: str
    existing_docstring: str | None = None


def _format_args(args: ast.arguments) -> str:
    parts = []
    for a in args.args:
        ann = ast.unparse(a.annotation) if a.annotation else None
        parts.append(f"{a.arg}: {ann}" if ann else a.arg)
    if args.vararg:
        parts.append(f"*{args.vararg.arg}")
    for a in args.kwonlyargs:
        ann = ast.unparse(a.annotation) if a.annotation else None
        parts.append(f"{a.arg}: {ann}" if ann else a.arg)
    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")
    return ", ".join(parts)


def _decorators(node) -> list[str]:
    return [ast.unparse(d) for d in getattr(node, "decorator_list", [])]


def _hash(*parts: str) -> str:
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


def extract_symbols(source: str) -> dict[str, Symbol]:
    """Returns {qualified_name: Symbol} for every top-level and class-level
    function/class in the file. Nested functions inside functions are
    skipped for now — docs target public-ish API surface, not internals."""
    tree = ast.parse(source)
    symbols: dict[str, Symbol] = {}

    def visit_function(node, prefix: str, kind: str):
        qualified_name = f"{prefix}{node.name}"
        args_str = _format_args(node.args)
        returns = ast.unparse(node.returns) if node.returns else None
        decorators = _decorators(node)

        signature = f"def {node.name}({args_str})" + (f" -> {returns}" if returns else "")
        sig_hash = _hash(args_str, returns or "", ",".join(sorted(decorators)))

        symbols[qualified_name] = Symbol(
            qualified_name=qualified_name,
            kind=kind,
            lineno=node.lineno,
            signature=signature,
            signature_hash=sig_hash,
            existing_docstring=ast.get_docstring(node),
        )

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            visit_function(node, "", "function")
        elif isinstance(node, ast.AsyncFunctionDef):
            visit_function(node, "", "async_function")
        elif isinstance(node, ast.ClassDef):
            bases = [ast.unparse(b) for b in node.bases]
            decorators = _decorators(node)
            sig_hash = _hash(",".join(bases), ",".join(sorted(decorators)))
            symbols[node.name] = Symbol(
                qualified_name=node.name,
                kind="class",
                lineno=node.lineno,
                signature=f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}",
                signature_hash=sig_hash,
                existing_docstring=ast.get_docstring(node),
            )
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    visit_function(item, f"{node.name}.", "function")
                elif isinstance(item, ast.AsyncFunctionDef):
                    visit_function(item, f"{node.name}.", "async_function")

    return symbols
