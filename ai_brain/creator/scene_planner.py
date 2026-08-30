"""
scene_planner.py
-----------------
Turns a movie idea + a list of available images/clips into a structured
scene plan (JSON) the video builder can execute mechanically. Keeping
"creative decisions" (AI) and "video assembly" (ffmpeg) in separate files
means you can swap either one out independently later.
"""

import json
from ai_brain import config
from ai_brain.ai_client import _get_client  # reuse the same configured client

PLANNER_SYSTEM_PROMPT = """You are a trailer scene planner. Given a movie
idea and a list of available image/clip filenames, output ONLY a JSON
array (no prose, no markdown fences) of scene objects, one per available
file, in dramatic trailer order (setup -> rising tension -> climax ->
title card). Each scene object must have exactly these keys:

- "file": one of the given filenames (use each file at most once)
- "text": a short punchy trailer caption for this scene (under 8 words,
  or "" for no text)
- "duration": seconds this scene should hold, a number between 2 and 5

Return exactly one scene per file provided, in the order you choose."""


def plan_scenes(idea: str, media_files: list[str]) -> list[dict]:
    """
    idea: e.g. "A lone astronaut discovers she's not alone on Mars"
    media_files: e.g. ["1.jpg", "2.jpg", "3.jpg"]
    returns: [{"file": "2.jpg", "text": "SHE THOUGHT SHE WAS ALONE", "duration": 3.5}, ...]
    """
    if not media_files:
        return []

    client = _get_client()
    if client is None:
        # Fallback: no API key configured yet — build a plain plan so the
        # video pipeline still works while you get set up.
        return [
            {"file": f, "text": "", "duration": 3.0}
            for f in media_files
        ]

    user_prompt = (
        f"Movie idea: {idea}\n"
        f"Available files: {json.dumps(media_files)}"
    )

    response = client.messages.create(
        model=config.AI_MODEL,
        max_tokens=1024,
        system=PLANNER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = response.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        # AI didn't return clean JSON — fail safe with a plain plan
        return [{"file": f, "text": "", "duration": 3.0} for f in media_files]

    # Basic validation: drop any scene referencing a file we don't have
    valid = [s for s in plan if s.get("file") in media_files]
    return valid or [{"file": f, "text": "", "duration": 3.0} for f in media_files]
