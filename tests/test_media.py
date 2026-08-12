"""Tests for local media generation."""

from io import BytesIO

from homeassistant.core import HomeAssistant
from PIL import Image

from custom_components.busybar.media import async_qr_png


async def test_qr_code_is_local_png(hass: HomeAssistant) -> None:
    """QR generation needs no network and fits the rear display."""
    filename, data = await async_qr_png(hass, "https://example.test/local")
    assert filename.endswith(".png")
    image = Image.open(BytesIO(data))
    assert image.format == "PNG"
    assert image.width <= 160
    assert image.height <= 80
