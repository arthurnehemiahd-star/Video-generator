````python
"""
scene_planner.py
-----------------
Creates a structured scene plan from a video idea.

The planner now creates:
    - a visual prompt for AI image generation
    - a short caption
    - a scene duration

The visual prompts are later passed to visual_generator.py.

The output is still JSON-compatible so the rest of the video
pipeline can work with it.
"""

import json
import re


DEFAULT_SCENE_COUNT = 5


def _clean_text(value: str) -> str:
    """Clean a piece of generated text."""

    if not isinstance(value, str):
        return ""

    return " ".join(value.strip().split())


def _extract_json_array(text: str) -> list:
    """
    Try to extract a JSON array from an AI/local response.

    This allows the planner to tolerate responses such as:

        ```json
        [...]
        ```

    or text surrounding the JSON.
    """

    if not text:
        return []

    text = text.strip()

    # Remove markdown fences.
    text = text.removeprefix("```json")
    text = text.removeprefix("```")
    text = text.removesuffix("```")
    text = text.strip()

    try:
        data = json.loads(text)

        if isinstance(data, list):
            return data

    except json.JSONDecodeError:
        pass

    # Try to locate the first JSON array.
    match = re.search(
        r"\[.*\]",
        text,
        flags=re.DOTALL,
    )

    if not match:
        return []

    try:
        data = json.loads(match.group(0))

        if isinstance(data, list):
            return data

    except json.JSONDecodeError:
        return []

    return []


def _fallback_scene_plan(
    idea: str,
    scene_count: int,
) -> list[dict]:
    """
    Create a useful local scene plan without an external AI API.

    This means the video generator can still work when no text AI
    service is configured.
    """

    idea = _clean_text(idea)

    if scene_count < 1:
        scene_count = DEFAULT_SCENE_COUNT

    scenes = []

    scene_roles = [
        (
            "Opening establishing shot",
            "Introduce the world, location and main subject."
        ),
        (
            "Character introduction",
            "Show the main subject beginning the journey."
        ),
        (
            "Rising action",
            "Introduce a problem, discovery or unexpected event."
        ),
        (
            "Climax",
            "Show the most dramatic and visually powerful moment."
        ),
        (
            "Ending",
            "Create a memorable cinematic final image."
        ),
    ]

    for index in range(scene_count):

        if index < len(scene_roles):
            role, direction = scene_roles[index]
        else:
            role = f"Story development scene {index + 1}"
            direction = (
                "Continue developing the story with strong "
                "cinematic visual storytelling."
            )

        prompt = (
            f"{idea}. "
            f"{role}. "
            f"{direction} "
            "Cinematic movie still, professional cinematography, "
            "dramatic lighting, detailed environment, "
            "strong composition, realistic depth, "
            "wide 16:9 composition."
        )

        captions = [
            "",
            "THE JOURNEY BEGINS",
            "SOMETHING HAS CHANGED",
            "EVERYTHING IS AT STAKE",
            "THE END IS ONLY THE BEGINNING",
        ]

        caption = captions[index] if index < len(captions) else ""

        scenes.append(
            {
                "prompt": prompt,
                "text": caption,
                "duration": 3.0,
            }
        )

    return scenes


def plan_scenes(
    idea: str,
    media_files: list[str] | None = None,
    scene_count: int = DEFAULT_SCENE_COUNT,
) -> list[dict]:
    """
    Create a scene plan.

    There are two supported modes.

    NEW AI-GENERATION MODE
    ----------------------
    When media_files is empty, the planner creates scene prompts:

        [
            {
                "prompt": "...",
                "text": "...",
                "duration": 3.0
            }
        ]

    LEGACY MEDIA MODE
    -----------------
    When media_files are provided, the planner creates scenes that
    reference those files. This keeps compatibility with the older
    version of the project.

    Args:
        idea:
            The user's video idea.

        media_files:
            Existing image filenames. Optional.

        scene_count:
            Number of scenes to create when generating new visuals.

    Returns:
        List of scene dictionaries.
    """

    idea = _clean_text(idea)

    if not idea:
        raise ValueError(
            "A video idea is required."
        )

    # ------------------------------------------------------------
    # NEW MODE
    #
    # No existing images were supplied.
    # Create prompts for the visual generator.
    # ------------------------------------------------------------

    if not media_files:

        return _fallback_scene_plan(
            idea=idea,
            scene_count=scene_count,
        )

    # ------------------------------------------------------------
    # LEGACY MODE
    #
    # Existing media files were supplied.
    # Keep the old behaviour so existing projects don't break.
    # ------------------------------------------------------------

    valid_files = [
        str(filename)
        for filename in media_files
        if str(filename).strip()
    ]

    if not valid_files:
        return _fallback_scene_plan(
            idea=idea,
            scene_count=scene_count,
        )

    scenes = []

    durations = [
        3.0,
        3.5,
        4.0,
        4.0,
        3.5,
    ]

    captions = [
        "",
        "THE JOURNEY BEGINS",
        "SOMETHING HAS CHANGED",
        "EVERYTHING IS AT STAKE",
        "THE END IS ONLY THE BEGINNING",
    ]

    for index, filename in enumerate(valid_files):

        duration = (
            durations[index]
            if index < len(durations)
            else 3.0
        )

        caption = (
            captions[index]
            if index < len(captions)
            else ""
        )

        scenes.append(
            {
                "file": filename,
                "text": caption,
                "duration": duration,
            }
        )

    return scenes


def plan_ai_scenes(
    idea: str,
    scene_count: int = DEFAULT_SCENE_COUNT,
) -> list[dict]:
    """
    Explicit helper for the new AI video-generation pipeline.

    This is the function trailer_builder.py can call when it wants
    brand-new AI-generated visuals rather than existing media.
    """

    return plan_scenes(
        idea=idea,
        media_files=None,
        scene_count=scene_count,
    )
````
