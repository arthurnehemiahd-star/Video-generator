"""
trailer_builder.py
-------------------
Orchestrates a full trailer build:
  1. Look at what media the user put in the project's media/ folder
  2. Ask the AI to plan scenes (order, captions, durations)
  3. Turn each image into a clip (ken burns + caption)
  4. Crossfade them together
  5. Mix in music, if the user provided one
  6. Save the final MP4 into the project folder

Video/audio clips (not just still images) can be dropped in too — this
first version treats every file as a still image, so short video clips
will just need to become a still frame or be extended later. That's a
natural next upgrade once this basic path is working end to end.
"""

import shutil
import tempfile
from pathlib import Path

from ai_brain.creator import scene_planner, ffmpeg_tools

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac"}


def build_trailer(project_dir: Path, idea: str) -> Path:
    media_dir = project_dir / "media"
    if not media_dir.exists():
        raise FileNotFoundError(
            f"No media/ folder found in {project_dir}. "
            f"Create it and add your images (and optionally one music file)."
        )

    all_files = sorted(media_dir.iterdir())
    images = [f for f in all_files if f.suffix.lower() in IMAGE_EXTS]
    music_files = [f for f in all_files if f.suffix.lower() in AUDIO_EXTS]

    if not images:
        raise FileNotFoundError(
            f"No images found in {media_dir}. Add some .jpg/.png files to build a trailer."
        )

    scene_plan = scene_planner.plan_scenes(idea, [f.name for f in images])

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        clip_paths = []

        for i, scene in enumerate(scene_plan):
            image_path = media_dir / scene["file"]
            clip_path = tmp_dir / f"clip_{i:03d}.mp4"
            ffmpeg_tools.image_to_clip(
                image_path=image_path,
                out_path=clip_path,
                duration=float(scene.get("duration", 3.0)),
                caption=scene.get("text", ""),
            )
            clip_paths.append(clip_path)

        concatenated = tmp_dir / "concatenated.mp4"
        ffmpeg_tools.concat_with_crossfade(clip_paths, concatenated)

        project_dir.mkdir(parents=True, exist_ok=True)
        final_path = project_dir / "trailer.mp4"

        if music_files:
            ffmpeg_tools.add_music(concatenated, music_files[0], final_path)
        else:
            shutil.copy(concatenated, final_path)

    return final_path
