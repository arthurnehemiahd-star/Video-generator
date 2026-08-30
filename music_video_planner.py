"""
music_video_planner.py
-----------------------
Given a song's cut points (from audio_analysis) and a list of media
files, asks the AI to assign each scene a caption (a lyric line, or a
mood/description if no lyrics are given) and pick which image goes in
which slot. Timing itself comes from the song's actual energy, not the
AI — the AI only handles the creative pairing of image <-> moment.
"""

import json
from ai_brain import config
from ai_brain.ai_client import _get_client

PLANNER_SYSTEM_PROMPT = """You are a music video scene planner. You will
be given: (1) a list of scene time windows with their duration in
seconds, and (2) a list of available image filenames, and (3) optional
lyrics or a mood/theme description. Output ONLY a JSON array (no prose,
no markdown fences), one object per scene window, in order, each with:

- "file": one of the given filenames (reuse files if there are more
  scenes than files; try to use each file at least once first)
- "text": a short caption for this scene — a lyric line if lyrics were
  given, otherwise a short mood phrase (under 8 words), or "" for none

Return exactly one object per scene window given, in the same order."""


def plan_music_video_scenes(
    media_files: list[str],
    scene_durations: list[float],
    lyrics_or_theme: str,
) -> list[dict]:
    """
    scene_durations: e.g. [2.3, 1.1, 2.6] — seconds per scene, already
    derived from the song's actual timing.
    returns: [{"file": "1.jpg", "text": "...", "duration": 2.3}, ...]
    """
    if not media_files or not scene_durations:
        return []

    client = _get_client()
    if client is None:
        # No API key yet: cycle through the images evenly so the video
        # pipeline still works while getting set up.
        return [
            {"file": media_files[i % len(media_files)], "text": "", "duration": d}
            for i, d in enumerate(scene_durations)
        ]

    user_prompt = (
        f"Scene windows (seconds): {json.dumps(scene_durations)}\n"
        f"Available files: {json.dumps(media_files)}\n"
        f"Lyrics or theme: {lyrics_or_theme}"
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
        plan = None

    if not plan or len(plan) != len(scene_durations):
        return [
            {"file": media_files[i % len(media_files)], "text": "", "duration": d}
            for i, d in enumerate(scene_durations)
        ]

    # Attach the real durations (AI doesn't get to override timing) and
    # validate each referenced file exists
    result = []
    for scene, duration in zip(plan, scene_durations):
        file = scene.get("file")
        if file not in media_files:
            file = media_files[0]
        result.append({"file": file, "text": scene.get("text", ""), "duration": duration})
    return result
