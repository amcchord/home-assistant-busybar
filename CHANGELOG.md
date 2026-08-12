# Changelog

All notable changes to BUSY Bar for Home Assistant are documented here.

## 0.2.1

- Update animation frames in place instead of globally clearing the Bar between every frame, eliminating the flicker and avoiding fights with the selected device app.
- Keep layer replacement clears scoped to Home Assistant's own application content.
- Pace generated effects against a stable frame clock so HTTP request time does not slow playback unnecessarily.
- Enlarge front and rear Image entity PNGs to at least 640 pixels wide with crisp nearest-neighbor scaling.
- Move BUSY Bar HTTP client construction off Home Assistant's event loop and repair the DHCP/zeroconf confirmation flow.

## 0.2.0

### Local interaction

- Add normalized local WebSocket events for every physical button, encoder turn, mode-switch position, and timer lifecycle transition.
- Add six Event entities, 19 visual device triggers, and the `busybar_event` event-bus contract.
- Add live front and rear screen Image entities.

### Native Home Assistant controls

- Add native Notify, Media Player, and Firmware Update entities.
- Add automatic-brightness, automatic-update, Bluetooth, and smart-home Switch entities.
- Add update-window Time entities and timer-profile state sensors.
- Add smart-home pairing buttons, including a locally generated rear-screen QR code.
- Add proactive Repairs for low storage, battery-blocked updates, failed updates, and unstable streaming.

### Display and media

- Add a priority-aware display layer compositor with expiry, stable layer updates, queued lower priorities, and restoration.
- Add 11 front/rear widgets, including countdown, chart, streak, and scoreboard layouts.
- Add local Home Assistant Media Source conversion for images, animations, video, and audio.
- Add local rear-screen QR generation, isolated asset cleanup, and an in-memory content-hash upload cache.
- Allow every custom action to target multiple BUSY Bars concurrently.

### Playfulness

- Expand to 22 bounded generated animations.
- Add 15 household presets with sensible messages, colors, durations, and priorities.
- Add Dice, Coin Flip, Magic 8-Ball, Reaction, Pong, Snake, and Pixel Pet mini-apps; interactive games use the physical controls.
- Add the auto-registered BUSY Bar Playground dashboard card with a draggable pixel canvas, widgets, effects, presets, games, profile editor, media tools, QR, and live preview.
- Add 13 schema-validated automation blueprints.

### Project quality

- Add a HACS-compatible brand icon and remove validation exemptions.
- Expand diagnostics, translations, visual action metadata, documentation, tests, and CI contracts.
- Validate widgets, QR, animation frames, both screen captures, and WebSocket connectivity against real BUSY Bar firmware 1.1.1 / API 25.0.0.

## 0.1.0

- Initial public local-first integration with config flow, DHCP discovery, resilient local state, timer controls, status scenes, notifications, basic effects, diagnostics, and HACS metadata.
