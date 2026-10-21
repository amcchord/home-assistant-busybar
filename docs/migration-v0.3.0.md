# Migrating to BUSY Bar Playground v0.3.0

Versions through v0.2.0 of this repository used the Home Assistant domain `busybar`. That domain belongs to the HACS integration [`pickerin/hass-busybar`](https://github.com/pickerin/hass-busybar). Both installed into `custom_components/busybar`, so one could overwrite the other. Starting with v0.3.0, this repository uses `busybar_playground` and the name **BUSY Bar Playground**.

Home Assistant treats this as a different integration. There is no automatic transfer of config entries or registries across domains, and no old-domain alias is installed because that would recreate the collision. Your Bar's firmware, HTTP API settings, stored timer profiles, and device-side `home_assistant` media namespace are unchanged.

## Before upgrading

1. Make a full Home Assistant backup, including your configuration and custom components. Record each Bar's address, optional API key, integration options, device ID, entity IDs, and the automations, scripts, scenes, notifications, and dashboards using them. Keep API keys private.
2. Disable affected automations while migrating. In **Settings → Devices & services**, remove the old **BUSY Bar** config entries created by **amcchord/home-assistant-busybar** while the old component is still installed. Entries created by `pickerin/hass-busybar` should be kept. If files have already been overwritten and ownership is unclear, restore your backup to identify the entries before proceeding.

## Install and configure

1. Update or re-download **amcchord/home-assistant-busybar** in HACS to v0.3.0 or later. Manual users should copy `custom_components/busybar_playground` to `/config/custom_components/busybar_playground`.
2. Check `/config/custom_components/busybar` for leftovers from this repository's old version. Remove that folder only if it belongs to this repository and you do not use `pickerin/hass-busybar`. Do not delete another integration's files; if both repositories previously targeted that folder, re-download `pickerin/hass-busybar` through its own HACS entry to restore its files. Do not rename or edit `.storage` entries by hand.
3. Restart Home Assistant. Add **BUSY Bar Playground** from **Settings → Devices & services → Add integration**, and enter each Bar's address and API key. Restore your integration options.
4. Check the new device and entity IDs. Home Assistant may allocate new IDs or suffixes; reselect them in automations, scripts, scenes, notifications, and dashboards. Do not assume the old device ID or an entity's old name maps to the new entry.

## Update consumers

| Reference | Through v0.2.0 | v0.3.0 and later |
| --- | --- | --- |
| Custom actions | `busybar.show_message`, `busybar.play_preset`, etc. | `busybar_playground.show_message`, `busybar_playground.play_preset`, etc. |
| Device trigger domain | `domain: busybar` | `domain: busybar_playground` |
| Device selectors | `integration: busybar` | `integration: busybar_playground` |
| Physical-input bus event | `busybar_event` | `busybar_playground_event` |
| Dashboard card type | `custom:busybar-card` | `custom:busybar-playground-card` |
| Manual dashboard module resource | `/busybar/busybar-card.js` | `/busybar_playground/busybar-playground-card.js` |

Update only consumers intended for this repository; calls intended for `pickerin/hass-busybar` retain its `busybar` domain and card type. Native actions such as `select.select_option` and `notify.send_message` keep their native domains but need the correct new entity targets. Check legacy per-device `notify.*` service names in Developer Tools after setup as well.

The card module registers automatically. Remove manually added old resource URLs, change your card type, reselect `device_id` and `preview_entity`, and reload the browser without cache. Do not remove the other integration's dashboard resources.

Re-import the blueprints you use from the same `blueprints/automation/busybar/` URLs. Their input names and source paths are stable, but their action domains and selectors changed. Reload automations, open each blueprint automation, and select the Playground device again. Update any locally edited blueprint copies and raw event automations too.

## Verify and recover

Confirm that the Playground entry loads without errors, its entities show the expected state, the new card loads, and a `busybar_playground.show_message` action reaches the intended Bar. Test one physical input trigger and each affected automation before re-enabling it. If also using `pickerin/hass-busybar`, check both entries and cards independently. Separate Home Assistant namespaces do not arbitrate simultaneous commands to one physical display; coordinate automations that control the same Bar.

If you need to roll back, restore the pre-upgrade Home Assistant backup and the matching v0.2.0 component. Reinstalling the old files alone does not restore removed config entries or registry references. Do not install v0.2.0 alongside `pickerin/hass-busybar`; it has the original domain collision.
