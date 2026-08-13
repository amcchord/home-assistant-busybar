"""Tests for desktop-friendly BUSY Bar screen previews."""

from io import BytesIO

from PIL import Image

from custom_components.busybar.image import _frame_to_png


def test_frame_preview_converts_bgr_and_uses_crisp_scaling() -> None:
    """BGR framebuffers open large with accurate, unblurred colors."""
    # Red, green, blue, yellow, cyan, and magenta encoded as BGR888.
    raw = bytes(
        (
            0,
            0,
            255,
            0,
            255,
            0,
            255,
            0,
            0,
            0,
            255,
            255,
            255,
            255,
            0,
            255,
            0,
            255,
        )
    )

    with Image.open(BytesIO(_frame_to_png(raw, 6, 1, 3))) as image:
        assert image.size == (18, 3)
        assert image.getpixel((0, 1)) == (255, 0, 0)
        assert image.getpixel((2, 1)) == (255, 0, 0)
        assert image.getpixel((3, 1)) == (0, 255, 0)
        assert image.getpixel((6, 1)) == (0, 0, 255)
        assert image.getpixel((9, 1)) == (255, 255, 0)
        assert image.getpixel((12, 1)) == (0, 255, 255)
        assert image.getpixel((15, 1)) == (255, 0, 255)
        assert image.getpixel((17, 1)) == (255, 0, 255)
