"""Simulated module: pull request review helpers (before a code change)."""


def review_pull_request(pr_number: int) -> dict:
    """Fetches a PR and runs it through the review pipeline."""
    ...


def format_comment(text: str) -> str:
    """Formats review feedback as a GitHub-flavored markdown comment."""
    ...


class PRReviewer:
    """Coordinates fetching, analyzing, and commenting on a pull request."""

    def run(self, pr_number: int) -> None:
        """Runs the full review flow for a single PR."""
        ...

    def score(self, diff_text: str) -> float:
        """Returns a 0-1 quality score for a diff."""
        ...
