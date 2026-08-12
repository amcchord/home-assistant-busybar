"""Local audio player entity for BUSY Bar."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BusyBarConfigEntry, BusyBarCoordinator
from .entity import BusyBarEntity
from .media import async_convert_asset, async_read_media_source


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BusyBarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the BUSY Bar audio player."""
    async_add_entities([BusyBarMediaPlayer(entry.runtime_data)])


class BusyBarMediaPlayer(BusyBarEntity, MediaPlayerEntity):
    """Play Home Assistant media-source audio through the device speaker."""

    _attr_translation_key = "audio"
    _attr_icon = "mdi:speaker-wireless"
    _attr_assumed_state = True
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.VOLUME_SET
    )

    def __init__(self, coordinator: BusyBarCoordinator) -> None:
        super().__init__(coordinator, "media_player")
        self._playing = False
        self._media_title: str | None = None

    @property
    def state(self) -> MediaPlayerState:
        """Return the best-known playback state."""
        return MediaPlayerState.PLAYING if self._playing else MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float | None:
        """Return volume in Home Assistant's 0..1 range."""
        volume = self.coordinator.data.snapshot.volume
        return volume.volume / 100 if volume and volume.volume is not None else None

    @property
    def media_title(self) -> str | None:
        """Return the last requested local media filename."""
        return self._media_title

    async def async_set_volume_level(self, volume: float) -> None:
        """Set speaker volume."""
        await self.coordinator._async_command(
            self.coordinator.api.audio_volume_set(max(0, min(100, volume * 100))),
            "set audio volume",
        )
        await self.coordinator.async_request_refresh()

    async def async_media_stop(self) -> None:
        """Stop current audio."""
        await self.coordinator.async_stop_sound()
        self._playing = False
        self.async_write_ha_state()

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        """Resolve, convert, upload, and play Home Assistant media."""
        filename, mime_type, data = await async_read_media_source(self.hass, media_id)
        if not mime_type.startswith("audio/"):
            raise HomeAssistantError("BUSY Bar audio player requires an audio file")
        converted_name, converted_data = await async_convert_asset(
            self.hass, filename, data
        )
        await self.coordinator.async_upload_asset(converted_name, converted_data)
        await self.coordinator.async_play_sound(path=converted_name)
        self._playing = True
        self._media_title = Path(filename).name
        self.async_write_ha_state()
