"""
video_generator.py
------------------
Turns a normal video description + requested duration into a finished MP4.
"""

import re
from pathlib import Path

from ai_brain import config, ai_client
from ai_brain.creator import image_generator, ffmpeg_tools


def _safe_name(text: str) -> str:
    """Make a safe project-folder name."""
    name = re.sub(r"[^a-zA-Z0-9_-]+", "-", text.strip().lower())
    name = name.strip("-")
    return name[:50] or "generated-video"


def _make_scene_prompts(description: str, duration: int) -> list[str]:
    """Ask the AI to create scene descriptions for the requested duration."""

    # Roughly one scene every 5 seconds.
    scene_count = max(2, min(24, round(duration / 5)))

    client = ai_client._get_client()

    if client is None:
        # Fallback if the AI isn't available.
        return [description] * scene_count

    prompt = f"""
Create {scene_count} visual scenes for this video:

{description}

The final video should be approximately {duration} seconds long.

Return ONLY a JSON array of strings.
Each string must be a detailed image-generation prompt.
Make the scenes visually connected and tell a clear story.
Do not include explanations or markdown.
"""

    response = client.messages.create(
        model=config.AI_MODEL,
        max_tokens=3000,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    import json

    raw = response.content[0].text.strip()
    raw = (
        raw.removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )

    try:
        scenes = json.loads(raw)
        if isinstance(scenes, list):
            scenes = [str(x) for x in scenes if str(x).strip()]
            if scenes:
                return scenes
    except json.JSONDecodeError:
        pass

    return [description] * scene_count


def generate_video(description: str, duration: int) -> Path:
    """
    Generate a complete video from a normal-language description.
    """

    if not description.strip():
        raise ValueError("Video description cannot be empty.")

    duration = int(duration)

    if duration < 5:
        raise ValueError("Video duration must be at least 5 seconds.")

    if duration > 120:
        raise ValueError("Video duration cannot exceed 120 seconds.")

    project_name = _safe_name(description)
    project_dir = config.PROJECTS_DIR / project_name
    media_dir = project_dir / "media"

    project_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)

    scenes = _make_scene_prompts(description, duration)

    scene_duration = duration / len(scenes)
    image_paths = []

    for index, scene_prompt in enumerate(scenes):
        image_path = media_dir / f"scene_{index + 1:03d}.png"

        image_generator.generate_image(
            prompt=scene_prompt,
            output_path=image_path,
        )

        image_paths.append(image_path)

    clip_paths = []

    for index, image_path in enumerate(image_paths):
        clip_path = project_dir / f"scene_{index + 1:03d}.mp4"

        ffmpeg_tools.image_to_clip(
            image_path=image_path,
            out_path=clip_path,
            duration=scene_duration,
        )

        clip_paths.append(clip_path)

    final_path = project_dir / "video.mp4"

    ffmpeg_tools.concat_with_crossfade(
        clip_paths,
        final_path,
    )

    return final_path
