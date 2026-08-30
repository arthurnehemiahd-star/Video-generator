"""
ai_client.py
------------
Thin wrapper around the Anthropic API. This is the ONLY file you'd need
to change to swap providers later (OpenAI, a local model via Ollama, etc.)
— everything else in the app just calls `get_ai_reply()`.
"""

from ai_brain import config

try:
    import anthropic
except ImportError:
    anthropic = None

SYSTEM_PROMPT = f"""You are {config.ASSISTANT_NAME}, a helpful personal AI
assistant running locally for one user. Be concise and practical. You can
be asked to run commands (prefixed with /), otherwise just chat normally."""


def _get_client():
    """
    Returns a configured Anthropic client, or None if the package isn't
    installed or no API key is set. Shared by ai_client and creator/
    modules so there's one place that knows how to build a client.
    """
    if anthropic is None or not config.ANTHROPIC_API_KEY:
        return None
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def get_ai_reply(history: list[dict]) -> str:
    """
    history: list of {"role": "user"|"assistant", "content": str}
    returns: the assistant's reply text
    """
    if anthropic is None:
        return ("[Error] The 'anthropic' package isn't installed yet. "
                "Run: pip install anthropic")

    if not config.ANTHROPIC_API_KEY:
        return ("[Error] No ANTHROPIC_API_KEY found. Copy .env.example to "
                ".env and add your key.")

    client = _get_client()

    try:
        response = client.messages.create(
            model=config.AI_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=history,
        )
        return response.content[0].text
    except Exception as e:
        return f"[Error talking to AI] {e}"
