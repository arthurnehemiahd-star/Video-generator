"""
trailer_builder.py
------------------

Builds a complete AI-generated trailer.

Workflow:

    1. Take the user's video idea.
    2. Create a cinematic scene plan.
    3. Generate an AI image for every scene.
    4. Turn each generated image into a moving video clip.
    5. Add captions.
    6. Crossfade the scenes together.
    7. Add optional background music.
    8. Save the finished MP4 as trailer.mp4.

The generated images are kept in a temporary directory, so the project's
media/ folder does not get filled with generated images.
"""

from pathlib import Path
import shutil
import tempfile

from ai_brain.creator import scene_planner
from ai_brain.creator import ffmpeg_tools
from ai_brain.creator import visual_generator


AUDIO_EXTS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
    ".flac",
}


def _find_music(media_dir: Path) -> list[Path]:
    """
    Find audio files inside the project's media/ directory.
    """
    if not media_dir.exists():
        return []

    return sorted(
        file
        for file in media_dir.iterdir()
        if file.is_file() and file.suffix.lower() in AUDIO_EXTS
    )


def _validate_scene_count(scene_count: int) -> int:
    """
    Keep the number of generated scenes within a reasonable range.
    """
    try:
        scene_count = int(scene_count)
    except (TypeError, ValueError):
        raise ValueError("scene_count must be a number.")

    if scene_count < 1:
        raise ValueError("scene_count must be at least 1.")

    if scene_count > 20:
        raise ValueError("scene_count cannot be greater than 20.")

    return scene_count


def build_trailer(
    project_dir: Path,
    idea: str,
    scene_count: int = 5,
) -> Path:
    """
    Generate a complete AI trailer.

    Parameters
    ----------
    project_dir:
        Directory belonging to the project.

    idea:
        The user's video/trailer idea.

    scene_count:
        Number of AI-generated scenes.

    Returns
    -------
    Path
        Path to the finished trailer.mp4 file.
    """

    if not idea or not idea.strip():
        raise ValueError("A video idea is required.")

    scene_count = _validate_scene_count(scene_count)

    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)

    media_dir = project_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    # Find optional background music.
    music_files = _find_music(media_dir)

    print()
    print("=" * 70)
    print("AI TRAILER GENERATOR")
    print("=" * 70)
    print(f"Idea: {idea}")
    print(f"Scenes: {scene_count}")
    print("=" * 70)
    print()

    # ------------------------------------------------------------------
    # STEP 1 — Create the scene plan
    # ------------------------------------------------------------------

    print("[1/5] Creating cinematic scene plan...")

    scene_plan = scene_planner.plan_ai_scenes(
        idea=idea,
        scene_count=scene_count,
    )

    if not scene_plan:
        raise RuntimeError("The scene planner did not create any scenes.")

    print(f"Created {len(scene_plan)} scenes.")

    # ------------------------------------------------------------------
    # STEP 2 — Generate AI images
    # ------------------------------------------------------------------

    with tempfile.TemporaryDirectory(prefix="ai_trailer_") as temp_folder:

        temp_dir = Path(temp_folder)

        generated_images_dir = temp_dir / "generated_images"
        generated_images_dir.mkdir(parents=True, exist_ok=True)

        print()
        print("[2/5] Generating AI images...")

        generated_scenes = []

        for index, scene in enumerate(scene_plan, start=1):

            prompt = str(scene.get("prompt", "")).strip()

            if not prompt:
                prompt = (
                    f"Cinematic movie scene based on this idea: {idea}. "
                    "Professional cinematography, dramatic lighting, "
                    "high detail, widescreen composition."
                )

            print()
            print(f"Generating scene {index}/{len(scene_plan)}...")
            print(f"Prompt: {prompt}")

            try:
                image_path = visual_generator.generate_scene_image(
                    scene_prompt=prompt,
                    output_dir=generated_images_dir,
                    scene_number=index,
                )

            except Exception as exc:
                raise RuntimeError(
                    f"Failed to generate AI image for scene {index}: {exc}"
                ) from exc

            generated_scenes.append(
                {
                    "image_path": Path(image_path),
                    "text": str(scene.get("text", "")).strip(),
                    "duration": float(scene.get("duration", 3.0)),
                }
            )

            print(f"Saved: {image_path}")

        # ------------------------------------------------------------------
        # STEP 3 — Turn images into video clips
        # ------------------------------------------------------------------

        print()
        print("[3/5] Turning AI images into video clips...")

        clips_dir = temp_dir / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)

        clip_paths = []

        for index, scene in enumerate(generated_scenes, start=1):

            image_path = scene["image_path"]
            caption = scene["text"]
            duration = scene["duration"]

            clip_path = clips_dir / f"scene_{index:03d}.mp4"

            print(
                f"Creating clip {index}/{len(generated_scenes)} "
                f"({duration:.1f}s)..."
            )

            try:
                ffmpeg_tools.image_to_clip(
                    image_path=image_path,
                    out_path=clip_path,
                    duration=duration,
                    caption=caption,
                )

            except Exception as exc:
                raise RuntimeError(
                    f"Failed to create video clip for scene {index}: {exc}"
                ) from exc

            clip_paths.append(clip_path)

        if not clip_paths:
            raise RuntimeError("No video clips were created.")

        # ------------------------------------------------------------------
        # STEP 4 — Combine all scenes
        # ------------------------------------------------------------------

        print()
        print("[4/5] Combining scenes with cinematic transitions...")

        combined_video = temp_dir / "combined.mp4"

        try:
            ffmpeg_tools.concat_with_crossfade(
                clip_paths=clip_paths,
                out_path=combined_video,
            )

        except Exception as exc:
            raise RuntimeError(
                f"Failed to combine video clips: {exc}"
            ) from exc

        # ------------------------------------------------------------------
        # STEP 5 — Add music and save final MP4
        # ------------------------------------------------------------------

        print()
        print("[5/5] Finalizing trailer...")

        final_path = project_dir / "trailer.mp4"

        if music_files:
            music_file = music_files[0]

            print(f"Adding music: {music_file.name}")

            try:
                ffmpeg_tools.add_music(
                    video_path=combined_video,
                    music_path=music_file,
                    out_path=final_path,
                )

            except Exception as exc:
                raise RuntimeError(
                    f"Failed to add background music: {exc}"
                ) from exc

        else:
            print("No background music found.")
            print("Saving trailer without music.")

            shutil.copy2(
                combined_video,
                final_path,
            )

    # ----------------------------------------------------------------------
    # Finished
    # ----------------------------------------------------------------------

    print()
    print("=" * 70)
    print("TRAILER COMPLETE")
    print("=" * 70)
    print(f"Output: {final_path}")
    print("=" * 70)
    print()

    return final_path
