# `prototype/doc_generator.py`

## `DailyQuotaExceeded`

```python
class DailyQuotaExceeded(Exception)
```

Raised when the free-tier per-day request cap is exceeded. Retrying will not succeed until the next daily reset, so callers should abort the current batch rather than consume remaining quota.

## `_is_daily_quota_error`

```python
def _is_daily_quota_error(exc: genai_errors.ClientError) -> bool
```

Determines whether a Gemini API client error is caused by exceeding the daily request quota rather than a per-minute rate limit. Inspects the error's quota identifier to distinguish between the two 429 causes.

## `generate_doc`

```python
def generate_doc(symbol: Symbol, retries: int) -> str
```

Calls Gemini to generate and return a docstring for a single symbol. Automatically retries on per-minute rate limits (429) by waiting, but immediately aborts on per-day rate limits.
