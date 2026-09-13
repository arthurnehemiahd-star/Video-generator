"""
visual_generator.py
-------------------
Generates visual scenes from text prompts.

The generated images are saved to disk so the existing FFmpeg
video pipeline can turn them into video clips.

This module is intentionally separate from ai_client.py:
- ai_client.py = local chat assistant
- visual_generator.py = AI visual generation
- ffmpeg_tools.py = video assembly
"""

from pathlib import Path
import os
import requests


# Hugging Face Inference API
HF_API_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    "stabilityai/stable-diffusion-xl-base-1.0"
)


class VisualGenerationError(RuntimeError):
    """Raised when an image cannot be generated."""
    pass


def _get_huggingface_token() -> str:
    """
    Gets the Hugging Face API token from the environment.

    Expected environment variable:

        HF_TOKEN=your_token_here
    """

    token = os.getenv("HF_TOKEN", "").strip()

    if not token:
        raise VisualGenerationError(
            "HF_TOKEN is not configured. "
            "Add your Hugging Face API token to the environment."
        )

    return token


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
            Description of the scene we want.

        output_path:
            Where the generated image should be saved.

        width:
            Desired image width.

        height:
            Desired image height.

    Returns:
        Path to the generated image.
    """

    prompt = str(prompt).strip()

    if not prompt:
        raise ValueError("Image generation prompt cannot be empty.")

    token = _get_huggingface_token()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
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
            timeout=180,
        )
    except requests.RequestException as exc:
        raise VisualGenerationError(
            f"Could not connect to Hugging Face: {exc}"
        ) from exc

    if response.status_code != 200:
        error_text = response.text[:2000]

        raise VisualGenerationError(
            "Hugging Face image generation failed.\n"
            f"HTTP status: {response.status_code}\n"
            f"Response: {error_text}"
        )

    content_type = response.headers.get("content-type", "")

    if not content_type.startswith("image/"):
        raise VisualGenerationError(
            "Hugging Face did not return an image.\n"
            f"Content-Type: {content_type}\n"
            f"Response: {response.text[:2000]}"
        )

    try:
        output_path.write_bytes(response.content)
    except OSError as exc:
        raise VisualGenerationError(
            f"Could not save generated image to {output_path}: {exc}"
        ) from exc

    return output_path


def generate_scene_image(
    scene_prompt: str,
    output_dir: Path,
    scene_number: int,
) -> Path:
    """
    Generate one numbered scene image.

    Example:

        generate_scene_image(
            "A spaceship crashes on Mars, cinematic lighting",
            Path("data/projects/MyProject/media"),
            1,
        )

    creates:

        data/projects/MyProject/media/generated_scene_001.png
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"generated_scene_{scene_number:03d}.png"

    cinematic_prompt = (
        f"{scene_prompt.strip()}, "
        "cinematic movie still, highly detailed, "
        "dramatic lighting, professional cinematography, "
        "wide composition, 16:9"
    )

    return generate_image(
        prompt=cinematic_prompt,
        output_path=output_path,
        width=1280,
        height=720,
    )


def generate_scene_images(
    scene_prompts: list[str],
    output_dir: Path,
) -> list[Path]:
    """
    Generate multiple scene images.

    Returns a list containing the paths of all generated images.
    """

    generated_images = []

    for index, prompt in enumerate(scene_prompts, start=1):
        image_path = generate_scene_image(
            scene_prompt=prompt,
            output_dir=output_dir,
            scene_number=index,
        )

        generated_images.append(image_path)

    return generated_images
