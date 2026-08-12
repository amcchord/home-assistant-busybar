"""Live front and rear display previews for BUSY Bar."""

from __future__ import annotations

from io import BytesIO
from math import ceil

from busylib import display as busy_display
from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util
from PIL import Image as PILImage

from .coordinator import BusyBarConfigEntry, BusyBarCoordinator
from .entity import BusyBarEntity

_PREVIEW_MIN_WIDTH = 640


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BusyBarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up screen preview images."""
    async_add_entities(
        (
            BusyBarScreenImage(hass, entry.runtime_data, "front"),
            BusyBarScreenImage(hass, entry.runtime_data, "back"),
        )
    )


class BusyBarScreenImage(BusyBarEntity, ImageEntity):
    """A PNG rendering of one physical BUSY Bar display."""

    _attr_content_type = "image/png"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: BusyBarCoordinator,
        display_name: str,
    ) -> None:
        ImageEntity.__init__(self, hass)
        BusyBarEntity.__init__(self, coordinator, f"{display_name}_screen")
        self._display_name = display_name
        self._attr_translation_key = f"{display_name}_screen"
        self._attr_icon = "mdi:monitor-screenshot"
        self._attr_image_last_updated = dt_util.utcnow()
        self._last_revision = coordinator.data.screen_revision

    async def async_image(self) -> bytes | None:
        """Fetch the current framebuffer and encode it as PNG."""
        raw = None
        if self._display_name == "front":
            raw = self.coordinator.data.snapshot.screen_front
        elif self.coordinator.data.snapshot.screen_back is not None:
            raw = self.coordinator.data.snapshot.screen_back
        if raw is None or self._display_name == "back":
            raw = await self.coordinator._async_command(
                self.coordinator.api.screen(self._display_name),
                f"capture the {self._display_name} display",
            )
        spec = busy_display.get_display_spec(self._display_name)
        expected = spec.width * spec.height * 3
        if not isinstance(raw, bytes) or len(raw) != expected:
            return None
        scale = max(1, ceil(_PREVIEW_MIN_WIDTH / spec.width))
        return await self.hass.async_add_executor_job(
            _frame_to_png, raw, spec.width, spec.height, scale
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Invalidate the frontend image when a new frame may be available."""
        revision = self.coordinator.data.screen_revision
        if self._display_name == "back" or revision != self._last_revision:
            self._last_revision = revision
            self._attr_image_last_updated = dt_util.utcnow()
            self._cached_image = None
        super()._handle_coordinator_update()


def _frame_to_png(raw: bytes, width: int, height: int, scale: int = 1) -> bytes:
    """Encode an RGB888 framebuffer as a crisp, desktop-friendly PNG."""
    image = PILImage.frombytes("RGB", (width, height), raw)
    if scale > 1:
        image = image.resize(
            (width * scale, height * scale),
            resample=PILImage.Resampling.NEAREST,
        )
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
