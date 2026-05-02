"""Per-request token accounting.

Pass a single TokenTracker through every Anthropic call inside one HTTP request
(classify -> retrieve -> answer). At the end of the request, call to_dict() to
get the usage object the benchmark expects, or None if no LLM was called.
"""
from __future__ import annotations


class TokenTracker:
    def __init__(self) -> None:
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.model: str | None = None

    def track(self, response, model: str) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        self.prompt_tokens += int(getattr(usage, "input_tokens", 0) or 0)
        self.completion_tokens += int(getattr(usage, "output_tokens", 0) or 0)
        # Record the most recent model — when multiple models are used in one
        # request we report the last one (typically the answer model, the one
        # whose tokens dominate).
        self.model = model

    def to_dict(self) -> dict | None:
        if self.prompt_tokens == 0 and self.completion_tokens == 0:
            return None
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "model": self.model,
        }
