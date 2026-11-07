import json
import os


def _client():
    """Return an Anthropic client when an API key is available."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
    except Exception:
        return None

    try:
        return anthropic.Anthropic(api_key=api_key)
    except Exception:
        return None


def _ask(system, user):
    """Send a prompt to Claude and return its plain text reply."""
    client = _client()
    if client is None:
        return None

    try:
        response = client.messages.create(
            model=os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307"),
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        for block in getattr(response, "content", []):
            if getattr(block, "type", None) == "text":
                return block.text
        return None
    except Exception:
        return None


def _json(text):
    """Extract the JSON object from a text blob and parse it."""
    if not text:
        return None

    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            return None
        return json.loads(text[start : end + 1])
    except Exception:
        return None
