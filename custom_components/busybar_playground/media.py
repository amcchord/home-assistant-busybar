"""Local Home Assistant media and QR helpers for BUSY Bar."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse

import segno
from busylib import converter
from busylib.converter import image as image_converter
from homeassistant.components import media_source
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.network import get_url

MAX_MEDIA_BYTES = 20 * 1024 * 1024


async def async_read_media_source(
    hass: HomeAssistant, media_content_id: str
) -> tuple[str, str, bytes]:
    """Resolve and read a Home Assistant media source with a strict size cap."""
    media = await media_source.async_resolve_media(
        hass, media_content_id, target_media_player=None
    )
    if media.path is not None:
        path = Path(media.path)
        size = await hass.async_add_executor_job(lambda: path.stat().st_size)
        if size > MAX_MEDIA_BYTES:
            raise HomeAssistantError("BUSY Bar media must be 20 MB or smaller")
        data = await hass.async_add_executor_job(path.read_bytes)
        return path.name, media.mime_type, data

    url = media.url
    if url.startswith("/"):
        url = get_url(hass, allow_internal=True, allow_external=False) + url
    response = await get_async_client(hass).get(url)
    response.raise_for_status()
    if len(response.content) > MAX_MEDIA_BYTES:
        raise HomeAssistantError("BUSY Bar media must be 20 MB or smaller")
    filename = Path(unquote(urlparse(url).path)).name or "media"
    return filename, media.mime_type, response.content


async def async_convert_asset(
    hass: HomeAssistant,
    filename: str,
    data: bytes,
    *,
    display: str = "front",
) -> tuple[str, bytes]:
    """Convert media into a device-native asset without blocking HA."""
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
    if Path(filename).suffix.lower() in image_extensions:
        converted = await hass.async_add_executor_job(
            lambda: image_converter.convert(filename, data, display_name=display)
        )
        if converted is None:
            raise HomeAssistantError("BUSY Bar image conversion returned no result")
        return converted
    return await hass.async_add_executor_job(
        converter.convert_for_storage, filename, data
    )


async def async_qr_png(hass: HomeAssistant, value: str) -> tuple[str, bytes]:
    """Generate a compact rear-screen QR code fully locally."""
    return await hass.async_add_executor_job(_qr_png, value)


def _qr_png(value: str) -> tuple[str, bytes]:
    qr = segno.make(value, error="m", micro=False)
    width, height = qr.symbol_size(scale=1, border=4)
    if width > 160 or height > 80:
        raise HomeAssistantError("QR value is too dense for the BUSY Bar rear display")
    scale = max(1, min(3, 80 // height))
    output = BytesIO()
    qr.save(
        output,
        kind="png",
        scale=scale,
        border=4,
        dark="#000000",
        light="#FFFFFF",
    )
    return "home-assistant-qr.png", output.getvalue()
