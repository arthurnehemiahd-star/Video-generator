"""
visual_generator.py
-------------------

Generates cinematic images from text prompts.

Pipeline:

    text prompt
        ↓
    Hugging Face Inference Providers
        ↓
    generated image
        ↓
    FFmpeg
        ↓
    video scene

This module is separate from:

    ai_client.py
        Local chat assistant

    scene_planner.py
        Creates the video scenes

    ffmpeg_tools.py
        Turns images into video and combines them
"""

from pathlib import Path
import os


try:
    from huggingface_hub import InferenceClient
except ImportError as exc:
    raise ImportError(
        "huggingface_hub is required for image generation. "
        "Install it with: pip install huggingface_hub"
    ) from exc


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"

DEFAULT_PROVIDER = "auto"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class VisualGenerationError(RuntimeError):
    """Raised when an image cannot be generated."""
    pass


# ---------------------------------------------------------------------------
# Hugging Face configuration
# ---------------------------------------------------------------------------

def _get_huggingface_token() -> str:
    """
    Get the Hugging Face token from the environment.

    Required environment variable:

        HF_TOKEN

    Example:

        HF_TOKEN=hf_xxxxxxxxxxxxxxxxx
    """

    token = os.getenv("HF_TOKEN", "").strip()

    if not token:
        raise VisualGenerationError(
            "HF_TOKEN is not configured.\n\n"
            "Create a Hugging Face token with inference permissions "
            "and add it to the environment as HF_TOKEN."
        )

    return token


def _get_model() -> str:
    """
    Get the image-generation model.

    Optional environment variable:

        HF_IMAGE_MODEL

    If it is not provided, FLUX.1-schnell is used.
    """

    model = os.getenv(
        "HF_IMAGE_MODEL",
        DEFAULT_MODEL,
    ).strip()

    return model or DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Create Hugging Face client
# ---------------------------------------------------------------------------

def _get_client() -> InferenceClient:
    """
    Create the Hugging Face InferenceClient.
    """

    token = _get_huggingface_token()

    try:
        client = InferenceClient(
            provider=DEFAULT_PROVIDER,
            api_key=token,
        )

    except Exception as exc:
        raise VisualGenerationError(
            f"Could not create Hugging Face client: {exc}"
        ) from exc

    return client


# ---------------------------------------------------------------------------
# Generate one image
# ---------------------------------------------------------------------------

def generate_image(
    prompt: str,
    output_path: Path,
    width: int = 1024,
    height: int = 576,
) -> Path:
    """
    Generate one image from a text prompt.

    Args:
        prompt:
            Description of the desired image.

        output_path:
            Where the generated PNG should be saved.

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

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    model = _get_model()

    client = _get_client()

    print()
    print("Starting AI image generation...")
    print(f"Model: {model}")
    print(f"Size: {width}x{height}")
    print()

    try:

        image = client.text_to_image(
            prompt=prompt,
            model=model,
            width=width,
            height=height,
        )

    except Exception as exc:

        raise VisualGenerationError(
            "Hugging Face image generation failed.\n"
            f"Model: {model}\n"
            f"Error: {exc}"
        ) from exc

    # -----------------------------------------------------------------------
    # Save the PIL image returned by Hugging Face
    # -----------------------------------------------------------------------

    try:

        image.save(
            output_path,
            format="PNG",
        )

    except Exception as exc:

        raise VisualGenerationError(
            f"Could not save generated image to "
            f"{output_path}: {exc}"
        ) from exc

    # -----------------------------------------------------------------------
    # Verify the file
    # -----------------------------------------------------------------------

    if not output_path.exists():

        raise VisualGenerationError(
            "The image generation request succeeded, "
            "but the image file was not created."
        )

    if output_path.stat().st_size == 0:

        raise VisualGenerationError(
            f"The generated image is empty: {output_path}"
        )

    print(
        f"Image saved successfully: {output_path}"
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

        generate_scene_image(
            scene_prompt=(
                "A young explorer walks through a futuristic "
                "city at night"
            ),
            output_dir=Path("generated"),
            scene_number=1,
        )

    creates:

        generated/generated_scene_001.png
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

    # -----------------------------------------------------------------------
    # Improve the planner's prompt for cinematic output
    # -----------------------------------------------------------------------

    cinematic_prompt = (
        f"{scene_prompt}. "
        "Cinematic movie still, "
        "professional cinematography, "
        "dramatic lighting, "
        "highly detailed environment, "
        "realistic textures, "
        "strong visual storytelling, "
        "wide cinematic composition, "
        "widescreen film frame."
    )

    print()
    print("=" * 70)
    print(
        f"GENERATING SCENE {scene_number}"
    )
    print("=" * 70)
    print(cinematic_prompt)
    print("=" * 70)

    return generate_image(
        prompt=cinematic_prompt,
        output_path=output_path,
        width=1024,
        height=576,
    )


# ---------------------------------------------------------------------------
# Generate multiple scenes
# ---------------------------------------------------------------------------

def generate_scene_images(
    scene_prompts: list[str],
    output_dir: Path,
) -> list[Path]:
    """
    Generate multiple cinematic scene images.

    Args:
        scene_prompts:
            List of scene descriptions.

        output_dir:
            Directory where images will be saved.

    Returns:
        List of generated image paths.
    """

    if not scene_prompts:

        raise ValueError(
            "scene_prompts cannot be empty."
        )

    generated_images: list[Path] = []

    total = len(scene_prompts)

    for index, prompt in enumerate(
        scene_prompts,
        start=1,
    ):

        print()
        print(
            f"Generating scene {index}/{total}..."
        )

        image_path = generate_scene_image(
            scene_prompt=prompt,
            output_dir=output_dir,
            scene_number=index,
        )

        generated_images.append(
            image_path
        )

    return generated_images
