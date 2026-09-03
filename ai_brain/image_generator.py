"""
video_generator.py
------------------
Turns a normal video description + requested duration into a finished MP4.

This version does NOT require Anthropic.
It creates connected visual prompts locally, then uses Hugging Face
to generate the images and FFmpeg to assemble the video.
"""

import re
from pathlib import Path

from ai_brain import config
from ai_brain.creator import image_generator, ffmpeg_tools


def _safe_name(text: str) -> str:
    """Make a safe project-folder name."""

    name = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "-",
        text.strip().lower(),
    )

    name = name.strip("-")

    return name[:50] or "generated-video"


def _make_scene_prompts(
    description: str,
    duration: int,
) -> list[str]:
    """
    Create visual scenes without using Anthropic.

    Each scene keeps the original description but adds a different
    cinematic moment so the final video feels like a story.
    """

    scene_count = max(
        2,
        min(12, round(duration / 5)),
    )

    scene_styles = [
        "wide establishing shot, cinematic atmosphere,",
        "medium shot, characters moving through the environment,",
        "close-up shot showing an important detail,",
        "dramatic shot with rising tension,",
        "dynamic cinematic shot showing action,",
        "emotional character moment,",
        "mysterious reveal,",
        "dramatic climax,",
        "powerful final shot,",
        "cinematic ending.",
        "beautiful closing shot.",
        "final dramatic scene.",
    ]

    prompts = []

    for index in range(scene_count):

        style = scene_styles[
            index % len(scene_styles)
        ]

        prompt = (
            f"{description}. "
            f"Scene {index + 1} of {scene_count}. "
            f"{style} "
            "Highly detailed cinematic photography, "
            "realistic lighting, dramatic composition, "
            "consistent characters and environment, "
            "professional film still, widescreen 16:9, "
            "no text, no subtitles, no watermark."
        )

        prompts.append(prompt)

    return prompts


def generate_video(
    description: str,
    duration: int,
) -> Path:
    """
    Generate a complete video from a normal-language description.
    """

    # -----------------------------
    # Validate input
    # -----------------------------

    if not description.strip():
        raise ValueError(
            "Video description cannot be empty."
        )

    duration = int(duration)

    if duration < 5:
        raise ValueError(
            "Video duration must be at least 5 seconds."
        )

    if duration > 120:
        raise ValueError(
            "Video duration cannot exceed 120 seconds."
        )

    # -----------------------------
    # Create project folders
    # -----------------------------

    project_name = _safe_name(
        description
    )

    project_dir = (
        config.PROJECTS_DIR /
        project_name
    )

    media_dir = (
        project_dir /
        "media"
    )

    project_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    media_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------
    # Create scene prompts
    # -----------------------------

    scenes = _make_scene_prompts(
        description,
        duration,
    )

    scene_duration = (
        duration / len(scenes)
    )

    image_paths = []

    # -----------------------------
    # Generate AI images
    # -----------------------------

    for index, scene_prompt in enumerate(
        scenes
    ):

        image_path = (
            media_dir /
            f"scene_{index + 1:03d}.png"
        )

        image_generator.generate_image(
            prompt=scene_prompt,
            output_path=image_path,
        )

        image_paths.append(
            image_path
        )

    # -----------------------------
    # Turn images into video clips
    # -----------------------------

    clip_paths = []

    for index, image_path in enumerate(
        image_paths
    ):

        clip_path = (
            project_dir /
            f"scene_{index + 1:03d}.mp4"
        )

        ffmpeg_tools.image_to_clip(
            image_path=image_path,
            out_path=clip_path,
            duration=scene_duration,
        )

        clip_paths.append(
            clip_path
        )

    # -----------------------------
    # Combine clips
    # -----------------------------

    final_path = (
        project_dir /
        "video.mp4"
    )

    ffmpeg_tools.concat_with_crossfade(
        clip_paths,
        final_path,
    )

    return final_path
