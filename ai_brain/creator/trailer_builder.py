```python
"""
trailer_builder.py
-------------------
Builds a complete AI-generated trailer.

Pipeline:

    1. Receive the user's video idea
    2. Generate scene descriptions
    3. Generate an AI image for every scene
    4. Turn each image into a video clip
    5. Crossfade the clips together
    6. Add music if available
    7. Save the final MP4

The user no longer needs to manually provide images.

Existing images can still be used if they are already present
in the project's media/ folder.
"""

import shutil
import tempfile
from pathlib import Path

from ai_brain.creator import (
    scene_planner,
    ffmpeg_tools,
    visual_generator,
)


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac"}


def _generate_scene_prompts(idea: str, number_of_scenes: int) -> list[str]:
    """
    Create scene prompts from the user's video idea.

    The first version uses a simple local prompt builder so the
    system can work without requiring another AI text API.

    Later we can replace this with a more advanced AI story planner.
    """

    if number_of_scenes <= 0:
        number_of_scenes = 5

    prompts = []

    for i in range(number_of_scenes):
        if i == 0:
            prompt = (
                f"{idea}. Opening establishing shot, "
                "introducing the world and main subject."
            )

        elif i == number_of_scenes - 1:
            prompt = (
                f"{idea}. Dramatic final scene, "
                "powerful cinematic ending."
            )

        else:
            prompt = (
                f"{idea}. Cinematic scene {i + 1}, "
                "developing the story with dramatic action "
                "and strong visual storytelling."
            )

        prompts.append(prompt)

    return prompts


def build_trailer(
    project_dir: Path,
    idea: str,
    number_of_scenes: int = 5,
) -> Path:
    """
    Generate a complete AI trailer.

    Args:
        project_dir:
            Project directory, for example:

                data/projects/MyProject

        idea:
            User's video description.

        number_of_scenes:
            Number of AI-generated scenes.

    Returns:
        Path to the final trailer.mp4 file.
    """

    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)

    media_dir = project_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    idea = str(idea).strip()

    if not idea:
        raise ValueError(
            "A video idea is required."
        )

    # ------------------------------------------------------------
    # STEP 1
    # Check for music supplied by the user.
    # ------------------------------------------------------------

    all_files = list(media_dir.iterdir())

    music_files = [
        f
        for f in all_files
        if f.is_file()
        and f.suffix.lower() in AUDIO_EXTS
    ]

    # ------------------------------------------------------------
    # STEP 2
    # Generate scene prompts.
    # ------------------------------------------------------------

    scene_prompts = _generate_scene_prompts(
        idea=idea,
        number_of_scenes=number_of_scenes,
    )

    # ------------------------------------------------------------
    # STEP 3
    # Generate AI images.
    # ------------------------------------------------------------

    generated_images = []

    try:
        for index, prompt in enumerate(scene_prompts, start=1):

            image_path = visual_generator.generate_scene_image(
                scene_prompt=prompt,
                output_dir=media_dir,
                scene_number=index,
            )

            generated_images.append(image_path)

    except Exception as exc:
        raise RuntimeError(
            "AI visual generation failed.\n\n"
            f"{exc}"
        ) from exc

    if not generated_images:
        raise RuntimeError(
            "No images were generated."
        )

    # ------------------------------------------------------------
    # STEP 4
    # Ask the scene planner to arrange the generated scenes.
    # ------------------------------------------------------------

    scene_plan = scene_planner.plan_scenes(
        idea,
        [image.name for image in generated_images],
    )

    if not scene_plan:
        scene_plan = [
            {
                "file": image.name,
                "text": "",
                "duration": 3.0,
            }
            for image in generated_images
        ]

    # ------------------------------------------------------------
    # STEP 5
    # Convert every generated image into a video clip.
    # ------------------------------------------------------------

    with tempfile.TemporaryDirectory() as tmp:

        tmp_dir = Path(tmp)
        clip_paths = []

        for index, scene in enumerate(scene_plan):

            image_path = media_dir / scene["file"]

            if not image_path.exists():
                continue

            clip_path = tmp_dir / f"clip_{index:03d}.mp4"

            ffmpeg_tools.image_to_clip(
                image_path=image_path,
                out_path=clip_path,
                duration=float(
                    scene.get("duration", 3.0)
                ),
                caption=scene.get("text", ""),
            )

            clip_paths.append(clip_path)

        if not clip_paths:
            raise RuntimeError(
                "No video clips could be created from the generated scenes."
            )

        # --------------------------------------------------------
        # STEP 6
        # Combine all scenes with crossfades.
        # --------------------------------------------------------

        concatenated = tmp_dir / "concatenated.mp4"

        ffmpeg_tools.concat_with_crossfade(
            clip_paths,
            concatenated,
        )

        # --------------------------------------------------------
        # STEP 7
        # Save final video.
        # --------------------------------------------------------

        final_path = project_dir / "trailer.mp4"

        if music_files:
            ffmpeg_tools.add_music(
                concatenated,
                music_files[0],
                final_path,
            )
        else:
            shutil.copy2(
                concatenated,
                final_path,
            )

    return final_path
```
