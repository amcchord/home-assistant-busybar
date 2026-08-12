# BUSY Bar for Home Assistant

[![Release](https://img.shields.io/github/v/release/amcchord/home-assistant-busybar?style=flat-square)](https://github.com/amcchord/home-assistant-busybar/releases)
[![Validate](https://img.shields.io/github/actions/workflow/status/amcchord/home-assistant-busybar/validate.yml?branch=main&label=validate&style=flat-square)](https://github.com/amcchord/home-assistant-busybar/actions/workflows/validate.yml)
[![Tests](https://img.shields.io/github/actions/workflow/status/amcchord/home-assistant-busybar/test.yml?branch=main&label=tests&style=flat-square)](https://github.com/amcchord/home-assistant-busybar/actions/workflows/test.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat-square)](#install-with-hacs)
[![License](https://img.shields.io/github/license/amcchord/home-assistant-busybar?style=flat-square)](LICENSE)

A playful, local-first [BUSY Bar](https://busy.app) integration for [Home Assistant](https://www.home-assistant.io). It reads device and focus state, exposes natural controls, delivers notifications, and turns the 72×16 display into a wonderfully overqualified household status board—entirely over your LAN.

No BUSY cloud account, webhooks, or internet connection is needed for everyday operation.

## Highlights

- Local push updates over the BUSY Bar status WebSocket, with resilient polling as a fallback.
- Battery, charging, Wi-Fi, firmware, storage, focus timer, pause, and update state.
- Brightness and volume sliders.
- Start, pause/resume, and stop focus sessions from Home Assistant.
- A native `notify` service plus a quick-message text entity.
- Status scenes: Available, Busy, Do Not Disturb, On Air, Meeting, Focus, Away, and Celebrate.
- Local animations: Rainbow, Scanner, Confetti, and Breathe.
- Rich services for messages, progress bars, one-off focus timers, virtual keys, and raw display elements.
- Priority-aware display ownership: normal automations do not stomp on an active BUSY session.
- Automatic DHCP discovery today and mDNS support ready for firmware that advertises `_busybar._tcp`.
- Redacted diagnostics, reauthentication, reconfiguration, and options flows.

## Install with HACS

Until this repository is included in HACS defaults, add it as a custom repository:

1. Open HACS in Home Assistant.
2. Select the three-dot menu, then **Custom repositories**.
3. Add `https://github.com/amcchord/home-assistant-busybar` as an **Integration**.
4. Install **BUSY Bar** and restart Home Assistant.

[![Open your Home Assistant instance and add this repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=amcchord&repository=home-assistant-busybar&category=integration)

For a manual install, copy `custom_components/busybar` into your Home Assistant configuration's `custom_components` directory and restart.

## Enable the local API

Open your BUSY Bar's local web interface, then enable Wi-Fi access for the HTTP API.

- **On**: leave the API key blank in Home Assistant.
- **Key**: enter the 4–10 digit local API key during setup.
- **Off**: Home Assistant cannot use protected local endpoints; the setup flow will explain how to enable them.

Using Key mode is recommended on shared or untrusted networks. The key stays in Home Assistant and is sent only to the device on your LAN.

## Add the integration

Go to **Settings → Devices & services → Add integration**, search for **BUSY Bar**, and enter the device's IP address or hostname. A discovered device may already be waiting on the Integrations page.

The integration creates one Home Assistant device with these entities:

| Kind | Entities |
| --- | --- |
| Sensors | Battery, Wi-Fi signal, power state, timer state, time remaining, current interval, firmware/API versions, uptime, free storage |
| Binary sensors | Busy, timer paused, charging, update available |
| Controls | Brightness, volume, status scene, quick message |
| Buttons | Start Busy, start Custom, pause/resume, stop, celebrate, clear HA display |

Diagnostic entities are disabled by default where Home Assistant considers them secondary.

## Display priority

BUSY Bar apps share the display through priorities:

| Priority | Meaning |
| ---: | --- |
| 10 | Normal built-in apps |
| 50 | This integration's safe default |
| 90 | Active BUSY or Custom work session |
| 100 | Explicit emergency override |

A service call that loses to a higher-priority app returns a clear Home Assistant error. Change the default under the integration's **Configure** menu, or override priority on a single service call. Use 91–100 sparingly.

## Services

### Colorful message

```yaml
action: busybar.show_message
data:
  device_id: YOUR_DEVICE_ID
  message: Dinner is ready!
  color: [74, 222, 128]
  background: [5, 46, 22]
  led_color: [34, 197, 94]
  duration: 15
```

Long text scrolls automatically. A duration of `0` keeps the message visible until `busybar.clear_display` is called.

### Progress bar

```yaml
action: busybar.show_progress
data:
  device_id: YOUR_DEVICE_ID
  value: 68
  label: 3D PRINT
  color: [56, 189, 248]
  duration: 30
```

### Celebration

```yaml
action: busybar.play_effect
data:
  device_id: YOUR_DEVICE_ID
  effect: confetti
  message: DONE!
  duration: 6
  fps: 8
```

Effects are generated locally and capped at 30 seconds so an automation cannot accidentally create an endless high-rate LAN workload.

### One-off focus session

```yaml
action: busybar.start_focus
data:
  device_id: YOUR_DEVICE_ID
  minutes: 50
  theme: on_air
  trigger_smart_home: true
```

This starts a timer snapshot without changing the Busy or Custom profiles stored on the device.

### Notify service

Home Assistant also creates a `notify` action named after the device:

```yaml
action: notify.busy_bar
data:
  title: Laundry
  message: The dryer finished
  data:
    color: "#FDE047FF"
    background: "#422006FF"
    duration: 20
```

### Raw drawing

`busybar.draw` accepts the official API's `DisplayElements` body, minus `application_name` (the integration safely supplies `home_assistant`). This unlocks text, rectangles, uploaded images/animations, countdowns, both displays, LED notification colors, and future firmware features.

See the [BUSY Bar API reference](https://api.busy.app/busybar/docs) for the element schema.

## Automation ideas

- Set **On Air** when a microphone-use or call sensor turns on, then return to **Available** afterward.
- Show the next calendar event five minutes before it begins.
- Put the washing machine's remaining percentage on the bar.
- Celebrate when everyone finishes their chores.
- Use a doorbell event to display `SOMEONE'S HERE` at priority 100.
- Start a 25-minute focus session when an NFC tag on the desk is scanned.
- Mirror alarm, air-quality, server, or 3D-printer status without sending household data to a cloud relay.

More complete recipes live in [docs/automations.md](docs/automations.md).

## Compatibility

- Home Assistant 2025.12 or newer.
- HACS 2.x.
- BUSY Bar firmware with local HTTP API support. The initial hardware validation used firmware **1.1.1** with API **25.0.0**.
- The official [`busylib`](https://github.com/busy-app/busylib-py) Python client is pinned and exercised by CI.

## Privacy and security

Normal operation talks directly from Home Assistant to the configured LAN address. The integration does not include analytics, telemetry, or cloud fallbacks. Diagnostics redact the API key, host, network names, addresses, serial number, and MAC addresses.

Read [SECURITY.md](SECURITY.md) before reporting a vulnerability.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt
pytest
ruff check .
ruff format --check .
```

Contributions, new scene ideas, and delightfully unnecessary pixel animations are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgements

This independent community integration is not affiliated with or endorsed by BUSY. BUSY Bar and related marks belong to their respective owner. It is built on BUSY's documented local API and official open-source Python client.

