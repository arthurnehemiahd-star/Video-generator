"""
image_generator.py
------------------
Generates images from text prompts using Hugging Face Inference Providers.
"""

import os
from pathlib import Path

from huggingface_hub import InferenceClient


MODEL = "black-forest-labs/FLUX.1-schnell"


def generate_image(prompt: str, output_path: Path) -> Path:
    """Generate one image and save it to output_path."""

    token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

    if not token:
        raise RuntimeError(
            "HUGGINGFACEHUB_API_TOKEN is not configured."
        )

    client = InferenceClient(
        provider="auto",
        api_key=token,
    )

    try:
        image = client.text_to_image(
            prompt=prompt,
            model=MODEL,
        )
    except Exception as e:
        raise RuntimeError(
            f"Image generation failed: {e}"
        ) from e

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)

    return output_path
