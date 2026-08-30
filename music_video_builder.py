"""
music_video_builder.py
------------------------
Orchestrates a full music video build:
  1. Find the song in the project's media/ folder
  2. Analyze it to find good cut points (audio_analysis.py)
  3. Ask the AI to assign images/captions to each resulting scene window
  4. Build each scene as a ken-burns clip with caption
  5. Hard-cut concatenate them (no crossfade — must stay beat-synced)
  6. Lay the full, untouched song under the video
  7. Save the final MP4 into the project folder
"""

import shutil
import tempfile
from pathlib import Path

from ai_brain.creator import audio_analysis, music_video_planner, ffmpeg_tools

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac"}


def build_music_video(project_dir: Path, lyrics_or_theme: str, scenes_per_minute: int = 20) -> Path:
    media_dir = project_dir / "media"
    if not media_dir.exists():
        raise FileNotFoundError(
            f"No media/ folder found in {project_dir}. "
            f"Add your images and exactly one song file."
        )

    all_files = sorted(media_dir.iterdir())
    images = [f for f in all_files if f.suffix.lower() in IMAGE_EXTS]
    music_files = [f for f in all_files if f.suffix.lower() in AUDIO_EXTS]

    if not images:
        raise FileNotFoundError(f"No images found in {media_dir}.")
    if not music_files:
        raise FileNotFoundError(
            f"No song found in {media_dir}. Add one .mp3/.wav/.m4a file — "
            f"the music video is built around its actual timing."
        )
    song_path = music_files[0]

    duration = audio_analysis.get_duration(song_path)
    num_scenes = max(2, min(40, round(duration / 60 * scenes_per_minute)))
    cut_points = audio_analysis.find_cut_points(song_path, num_scenes)

    boundaries = [0.0] + cut_points + [duration]
    scene_durations = [round(boundaries[i + 1] - boundaries[i], 2) for i in range(len(boundaries) - 1)]
    scene_durations = [d for d in scene_durations if d > 0.1]

    scene_plan = music_video_planner.plan_music_video_scenes(
        [f.name for f in images], scene_durations, lyrics_or_theme
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        clip_paths = []

        for i, scene in enumerate(scene_plan):
            image_path = media_dir / scene["file"]
            clip_path = tmp_dir / f"clip_{i:03d}.mp4"
            ffmpeg_tools.image_to_clip(
                image_path=image_path,
                out_path=clip_path,
                duration=float(scene["duration"]),
                caption=scene.get("text", ""),
            )
            clip_paths.append(clip_path)

        concatenated = tmp_dir / "concatenated.mp4"
        ffmpeg_tools.concat_hard(clip_paths, concatenated)

        project_dir.mkdir(parents=True, exist_ok=True)
        final_path = project_dir / "music_video.mp4"
        ffmpeg_tools.mux_full_track(concatenated, song_path, final_path)

    return final_path
