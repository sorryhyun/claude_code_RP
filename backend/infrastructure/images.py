"""
Image utilities for WebP conversion.

Converts images to WebP format for better compression (25-35% smaller than JPEG/PNG).
"""

import base64
import io
import os
from typing import Tuple

from PIL import Image

# WebP quality (1-100)
WEBP_QUALITY = int(os.getenv("IMAGE_WEBP_QUALITY", "95"))


def compress_image_base64(
    base64_data: str,
    media_type: str,
) -> Tuple[str, str]:
    """
    Convert a base64-encoded image to WebP format.

    Args:
        base64_data: Base64-encoded image data (without data URL prefix)
        media_type: MIME type of the image (e.g., 'image/png', 'image/jpeg')

    Returns:
        Tuple of (webp_base64_data, 'image/webp')

    Note:
        If conversion fails, returns original data unchanged.
    """
    # Skip if already WebP
    if media_type == "image/webp":
        return base64_data, media_type

    try:
        # Decode base64 to bytes
        image_bytes = base64.b64decode(base64_data)

        # Open image with Pillow
        image = Image.open(io.BytesIO(image_bytes))

        # Handle palette mode (P) for transparency
        if image.mode == "P":
            image = image.convert("RGBA")

        # Convert to WebP
        output_buffer = io.BytesIO()
        image.save(
            output_buffer,
            format="WEBP",
            quality=WEBP_QUALITY,
            method=6,  # Better compression
        )
        compressed_bytes = output_buffer.getvalue()

        # Encode back to base64
        compressed_base64 = base64.b64encode(compressed_bytes).decode("utf-8")

        return compressed_base64, "image/webp"

    except Exception as e:
        # If conversion fails, return original
        print(f"WebP conversion failed: {e}")
        return base64_data, media_type
