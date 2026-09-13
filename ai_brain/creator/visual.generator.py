"""
visual_generator.py
-------------------

Generates visual scenes from text prompts.

Pipeline:

    Text prompt
        ↓
    Hugging Face image generation
        ↓
    PNG image
        ↓
    FFmpeg
        ↓
    Video scene

This module is intentionally separate from ai_client.py:

    ai_client.py          = local chat assistant
    visual_generator.py   = AI visual generation
    ffmpeg_tools.py       = video assembly
"""

from pathlib import Path
import os

import requests


# ---------------------------------------------------------------------------
# Hugging Face
# ---------------------------------------------------------------------------

HF_API_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    "stabilityai/stable-diffusion-xl-base-1.0"
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class VisualGenerationError(RuntimeError):
    """Raised when an AI image cannot be generated."""
    pass


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _get_huggingface_token() -> str:
    """
    Read the Hugging Face API token from the environment.

    Required:

        HF_TOKEN=your_hugging_face_token
    """

    token = os.getenv("HF_TOKEN", "").strip()

    if not token:
        raise VisualGenerationError(
            "HF_TOKEN is not configured.\n"
            "Add your Hugging Face API token to the environment."
        )

    return token


# ---------------------------------------------------------------------------
# Generate one image
# ---------------------------------------------------------------------------

def generate_image(
    prompt: str,
    output_path: Path,
    width: int = 1280,
    height: int = 720,
) -> Path:
    """
    Generate one image from a text prompt.

    Args:
        prompt:
            Description of the scene.

        output_path:
            File where the generated image will be saved.

        width:
            Requested image width.

        height:
            Requested image height.

    Returns:
        Path to the generated image.
    """

    prompt = str(prompt).strip()

    if not prompt:
        raise ValueError(
            "Image generation prompt cannot be empty."
        )

    token = _get_huggingface_token()

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "image/png",
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "width": width,
            "height": height,
        },
    }

    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            json=payload,
            timeout=300,
        )

    except requests.Timeout as exc:
        raise VisualGenerationError(
            "Hugging Face image generation timed out."
        ) from exc

    except requests.RequestException as exc:
        raise VisualGenerationError(
            f"Could not connect to Hugging Face: {exc}"
        ) from exc

    # -----------------------------------------------------------------------
    # Hugging Face returned an error
    # -----------------------------------------------------------------------

    if response.status_code != 200:

        error_text = response.text[:3000]

        raise VisualGenerationError(
            "Hugging Face image generation failed.\n"
            f"HTTP status: {response.status_code}\n"
            f"Response: {error_text}"
        )

    # -----------------------------------------------------------------------
    # Verify that we actually received an image
    # -----------------------------------------------------------------------

    content_type = response.headers.get(
        "content-type",
        "",
    ).lower()

    if not content_type.startswith("image/"):

        try:
            response_text = response.text[:3000]
        except Exception:
            response_text = "<unable to read response>"

        raise VisualGenerationError(
            "Hugging Face did not return an image.\n"
            f"Content-Type: {content_type}\n"
            f"Response: {response_text}"
        )

    # -----------------------------------------------------------------------
    # Save image
    # -----------------------------------------------------------------------

    try:

        output_path.write_bytes(
            response.content
        )

    except OSError as exc:

        raise VisualGenerationError(
            f"Could not save generated image to "
            f"{output_path}: {exc}"
        ) from exc

    if not output_path.exists():
        raise VisualGenerationError(
            f"Image generation completed, but "
            f"{output_path} was not created."
        )

    if output_path.stat().st_size == 0:
        raise VisualGenerationError(
            f"Generated image is empty: {output_path}"
        )

    return output_path


# ---------------------------------------------------------------------------
# Generate one cinematic scene
# ---------------------------------------------------------------------------

def generate_scene_image(
    scene_prompt: str,
    output_dir: Path,
    scene_number: int,
) -> Path:
    """
    Generate one numbered cinematic scene.

    Example:

        scene_prompt =
            "A young explorer discovers an ancient city on Mars"

    Output:

        generated_scene_001.png
    """

    scene_prompt = str(scene_prompt).strip()

    if not scene_prompt:
        raise ValueError(
            "Scene prompt cannot be empty."
        )

    try:
        scene_number = int(scene_number)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "scene_number must be a number."
        ) from exc

    if scene_number < 1:
        raise ValueError(
            "scene_number must be at least 1."
        )

    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / f"generated_scene_{scene_number:03d}.png"
    )

    # Add cinematic instructions to the planner's prompt.
    cinematic_prompt = (
        f"{scene_prompt}, "
        "cinematic movie still, "
        "professional cinematography, "
        "dramatic lighting, "
        "high detail, "
        "realistic textures, "
        "strong visual storytelling, "
        "wide cinematic composition, "
        "16:9 aspect ratio"
    )

    print(
        f"Generating visual scene {scene_number}..."
    )

    image_path = generate_image(
        prompt=cinematic_prompt,
        output_path=output_path,
        width=1280,
        height=720,
    )

    print(
        f"Scene {scene_number} generated: "
        f"{image_path}"
    )

    return image_path


# ---------------------------------------------------------------------------
# Generate multiple scenes
# ---------------------------------------------------------------------------

def generate_scene_images(
    scene_prompts: list[str],
    output_dir: Path,
) -> list[Path]:
    """
    Generate multiple scene images.

    Args:
        scene_prompts:
            List of cinematic scene descriptions.

        output_dir:
            Directory where the generated images will be stored.

    Returns:
        List of generated image paths.
    """

    if not scene_prompts:
        raise ValueError(
            "scene_prompts cannot be empty."
        )

    generated_images: list[Path] = []

    for index, prompt in enumerate(
        scene_prompts,
        start=1,
    ):

        image_path = generate_scene_image(
            scene_prompt=prompt,
            output_dir=output_dir,
            scene_number=index,
        )

        generated_images.append(
            image_path
        )

    return generated_images
