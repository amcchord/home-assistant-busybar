"""Tests for desktop-friendly BUSY Bar screen previews."""

from io import BytesIO

from PIL import Image

from custom_components.busybar.image import _frame_to_png


def test_frame_preview_uses_crisp_nearest_neighbor_scaling() -> None:
    """Tiny framebuffers open large without introducing blurry colors."""
    raw = bytes((255, 0, 0, 0, 255, 0))

    with Image.open(BytesIO(_frame_to_png(raw, 2, 1, 3))) as image:
        assert image.size == (6, 3)
        assert image.getpixel((0, 1)) == (255, 0, 0)
        assert image.getpixel((2, 1)) == (255, 0, 0)
        assert image.getpixel((3, 1)) == (0, 255, 0)
        assert image.getpixel((5, 1)) == (0, 255, 0)
