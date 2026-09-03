"""
ai_client.py
------------
Local AI assistant fallback.

This version does NOT use Anthropic or any external AI API.
The video generator does not depend on this file.
"""


def _get_client():
    """
    Kept for compatibility with older parts of the project.

    There is no external AI client anymore.
    """
    return None


def get_ai_reply(history: list[dict]) -> str:
    """
    Simple local assistant.

    history:
        list of {"role": "user"|"assistant", "content": str}

    returns:
        assistant reply
    """

    if not history:
        return "Hey bro! What are we building today? 🎬"

    last_message = history[-1].get(
        "content",
        ""
    ).strip().lower()

    if not last_message:
        return "Tell me what we want to do."

    if "hello" in last_message or "hi" in last_message:
        return "Hey bro! 👋 Our video generator is ready."

    if "video" in last_message:
        return (
            "🎬 We can create a video by entering a description "
            "and choosing a duration."
        )

    if "help" in last_message:
        return (
            "Try the video generator above. "
            "Describe the video we want, choose the duration, "
            "then click Generate Video."
        )

    return (
        "I'm running in local mode right now, bro. "
        "The video generator is the main system we're building. 🎬"
    )
