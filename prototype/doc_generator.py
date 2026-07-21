"""
Turns diffed symbols into generated documentation via Gemini.

Kept separate from symbol_extractor/differ on purpose: those two are pure,
deterministic, and easy to test without any API key. This module is the
only place that talks to the network, so it's the only place that needs
GEMINI_API_KEY set and the only place that can fail on rate limits/quota.
"""
import os

from google import genai

from prototype.symbol_extractor import Symbol

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

PROMPT_TEMPLATE = """You are writing API documentation for a Python codebase.

Symbol: {qualified_name}
Kind: {kind}
Signature: {signature}
Existing docstring (may be outdated or missing): {existing_docstring}

Write a concise, accurate docstring for this symbol based on its signature.
Rules:
- 1-3 sentences. No filler like "This function...".
- Mention parameters only if their purpose isn't obvious from the name/type.
- Do not invent behavior that isn't implied by the name/signature/types.
- Return ONLY the docstring text, no quotes, no markdown fences.
"""


def _client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Export it before running doc generation:\n"
            "    export GEMINI_API_KEY=your_key_here"
        )
    return genai.Client(api_key=api_key)


def generate_doc(symbol: Symbol) -> str:
    """Calls Gemini once for a single symbol and returns the generated docstring text."""
    client = _client()
    prompt = PROMPT_TEMPLATE.format(
        qualified_name=symbol.qualified_name,
        kind=symbol.kind,
        signature=symbol.signature,
        existing_docstring=symbol.existing_docstring or "(none)",
    )

    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text.strip()


def generate_docs_for_symbols(symbols: list[Symbol]) -> dict[str, str]:
    """Runs generate_doc for a batch of symbols. Sequential on purpose for
    the prototype — batching/concurrency is a Celery-layer concern, not this
    module's job."""
    results = {}
    for symbol in symbols:
        results[symbol.qualified_name] = generate_doc(symbol)
    return results