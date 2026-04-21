from anthropic import Anthropic, APIError, APIStatusError
from fastapi import HTTPException
from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, CLAUDE_MODEL

_kwargs = {"api_key": ANTHROPIC_API_KEY}
if ANTHROPIC_BASE_URL:
    _kwargs["base_url"] = ANTHROPIC_BASE_URL

_client = Anthropic(**_kwargs)


class LLMError(Exception):
    pass


def chat(system: str, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.7) -> str:
    """Send a chat turn to Claude and return the text content.

    Raises HTTPException(502) on API errors so FastAPI surfaces a clean message
    to the client instead of a 500.
    """
    try:
        resp = _client.messages.create(
            model=CLAUDE_MODEL,
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
    parts = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def complete(prompt: str, max_tokens: int = 1024, temperature: float = 0.3) -> str:
    """One-shot completion: send a single user message and return the text."""
    return chat(system="", messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens, temperature=temperature)
