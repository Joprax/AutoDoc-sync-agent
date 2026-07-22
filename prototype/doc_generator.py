"""
Turns diffed symbols into generated documentation via Gemini.

Kept separate from symbol_extractor/differ on purpose: those two are pure,
deterministic, and easy to test without any API key. This module is the
only place that talks to the network, so it's the only place that needs
GEMINI_API_KEY set and the only place that can fail on rate limits/quota.
"""
import os
import time

from google import genai
from google.genai import errors as genai_errors

from prototype.symbol_extractor import Symbol

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Google's free tier for gemini-2.5-flash allows 5 requests/minute.
# Spacing calls at 13s apart keeps us under that (60s / 5 = 12s minimum,
# 13s gives a small safety margin) instead of firing them back-to-back
# and hitting a 429 partway through a batch.
FREE_TIER_DELAY_SECONDS = 13

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


class DailyQuotaExceeded(Exception):
    """Raised when the free-tier per-day request cap is hit. Retrying won't
    help — it only resets at the next day boundary — so callers should stop
    the whole batch rather than continue burning remaining quota on retries."""


def _client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Export it before running doc generation:\n"
            "    export GEMINI_API_KEY=your_key_here"
        )
    return genai.Client(api_key=api_key)


def _is_daily_quota_error(exc: genai_errors.ClientError) -> bool:
    """The free tier has two separate 429 causes: per-minute (retryable after
    a short wait) and per-day (fixed at 20 requests, does not reset soon).
    We tell them apart by checking the quotaId Google includes in the error."""
    message = str(exc)
    return "PerDay" in message


def generate_doc(symbol: Symbol, retries: int = 3) -> str:
    """Calls Gemini once for a single symbol and returns the generated docstring text.
    Retries on a per-minute 429 by waiting; immediately gives up on a per-day
    429 since no amount of waiting today will fix that."""
    client = _client()
    prompt = PROMPT_TEMPLATE.format(
        qualified_name=symbol.qualified_name,
        kind=symbol.kind,
        signature=symbol.signature,
        existing_docstring=symbol.existing_docstring or "(none)",
    )

    for attempt in range(retries):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            return response.text.strip()
        except genai_errors.ClientError as exc:
            if exc.code != 429:
                raise
            if _is_daily_quota_error(exc):
                raise DailyQuotaExceeded(
                    "Free-tier daily quota (20 requests/day) for this model is used up. "
                    "It resets roughly 24h after your first request today — try again "
                    "tomorrow, or test with fewer symbols via --limit."
                ) from exc
            if attempt < retries - 1:
                wait_seconds = FREE_TIER_DELAY_SECONDS * (attempt + 1)
                print(f"    (rate limited on {symbol.qualified_name}, waiting {wait_seconds}s...)")
                time.sleep(wait_seconds)
                continue
            raise


def generate_docs_for_symbols(symbols: list[Symbol]) -> dict[str, str]:
    """Runs generate_doc for a batch of symbols, sequentially, with a fixed
    delay between calls to stay under the free-tier per-minute rate limit.
    Stops immediately (keeping whatever was generated so far) if the daily
    quota is hit, rather than losing partial progress to an unhandled crash."""
    results = {}
    for i, symbol in enumerate(symbols):
        if i > 0:
            time.sleep(FREE_TIER_DELAY_SECONDS)
        try:
            results[symbol.qualified_name] = generate_doc(symbol)
        except DailyQuotaExceeded as exc:
            print(f"\n{exc}")
            print(f"Generated {len(results)}/{len(symbols)} before stopping.")
            break
    return results