from anthropic import Anthropic, APIError, APIStatusError
from fastapi import HTTPException
from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, CLAUDE_MODEL, MODELS
from services.token_tracker import TokenTracker

_kwargs = {"api_key": ANTHROPIC_API_KEY}
if ANTHROPIC_BASE_URL:
    _kwargs["base_url"] = ANTHROPIC_BASE_URL

_client = Anthropic(**_kwargs)


class LLMError(Exception):
    pass


def _resolve_model(model: str | None, tier: str | None) -> str:
    """Pick the model to use. Explicit `model` wins; otherwise look up `tier`
    in MODELS; otherwise fall back to the env-default CLAUDE_MODEL."""
    if model:
        return model
    if tier:
        return MODELS.get(tier, CLAUDE_MODEL)
    return CLAUDE_MODEL


def chat(
    system: str,
    messages: list[dict],
    max_tokens: int = 1024,
    temperature: float = 0.7,
    model: str | None = None,
    tier: str | None = None,
    tracker: TokenTracker | None = None,
) -> str:
    """Send a chat turn to Claude and return the text content.

    Pass `tier="fast"` or `tier="quality"` to use the routing config.
    Pass a `tracker` to accumulate token usage for the current request.
    """
    chosen = _resolve_model(model, tier)
    try:
        resp = _client.messages.create(
            model=chosen,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
    except APIStatusError as e:
        status = getattr(e, "status_code", 502)
        raise HTTPException(
            status_code=502,
            detail=f"Claude API error ({status}): {e.message if hasattr(e, 'message') else str(e)}",
        ) from e
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {e}") from e

    if tracker is not None:
        tracker.track(resp, chosen)

    parts = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def complete(
    prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    model: str | None = None,
    tier: str | None = None,
    tracker: TokenTracker | None = None,
) -> str:
    """One-shot completion: send a single user message and return the text."""
    return chat(
        system="",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
        model=model,
        tier=tier,
        tracker=tracker,
    )
