# BUSY Bar Playground card

The integration bundles a dashboard card and registers its JavaScript module during setup. No separate frontend repository is required.

## Add the card

Add a manual dashboard card:

```yaml
type: custom:busybar-card
device_id: YOUR_DEVICE_ID
preview_entity: image.your_busy_bar_front_screen
title: BUSY Bar Playground
```

Find the device ID in the URL while viewing the BUSY Bar device page, or select it in a visual action and inspect the generated YAML. The preview entity is optional but recommended.

If the custom card type is not immediately available after upgrading, reload the browser without cache or restart Home Assistant. The module URL is `/busybar/busybar-card.js` and includes the integration version as a cache key.

## Compose

Choose one of eleven widgets, the front or rear screen, colors, lifetime, and priority. Specialized widgets interpret the value field as follows:

- Progress: a number from 0 to 100.
- Countdown: an ISO timestamp.
- Chart: comma-separated numeric values.
- Streak: the count in Value and a label such as `DAYS` in Unit when called from an action.
- Scoreboard: compact text such as `ALEX 12 • SAM 9`.
- All others: friendly text.

Widgets restore the previous eligible display layer after they expire.

## Canvas

Canvas maps directly onto the physical resolution: 72×16 on the front and 160×80 on the rear. Drag the text in the preview or enter exact X/Y coordinates, choose a firmware font and colors, then draw. This is intended for quick compositions; `busybar.draw` remains available for multi-element rectangles, images, animations, and countdowns.

## Effects and household shortcuts

Household shortcuts choose an animation, color, message, duration, and sensible priority together. The Animation Lab exposes all effects directly when you want to choose the look yourself.

Generated frames are sent over the LAN, bounded at 12 FPS and 30 seconds, and occupy one restorable display layer.

## Games

Dice, Coin Flip, Magic 8-Ball, and Pixel Pet are one-shot mini-apps. Reaction accepts any physical button press after “GO.” Pong uses the encoder or OK/Back buttons. Snake turns with the encoder. A mini-app ends after its configured bound and restores what was underneath.

## Profiles

The profile editor changes the timer profile physically stored in the Busy or Custom switch slot. Infinite, simple, and work/rest interval timers are supported. These are persistent device settings, unlike the one-off `busybar.start_focus` action.

## Media and QR

Paste a Home Assistant Media Source ID selected from an automation media selector. Images and animations can target either display; audio plays through the speaker. QR content is generated locally and targets the rear display.

Inputs are capped at 20 MB. Large or dense QR content is rejected before upload. **Delete assets** in the integration actions removes only files in Home Assistant's BUSY Bar namespace.
