# Automation recipes

Replace `YOUR_DEVICE_ID` and example entity IDs with those from your Home Assistant instance.

## Show when you are on a call

```yaml
alias: BUSY Bar - on a call
triggers:
  - trigger: state
    entity_id: binary_sensor.microphone_in_use
    to: "on"
actions:
  - action: select.select_option
    target:
      entity_id: select.busy_bar_status_scene
    data:
      option: on_air
```

Create a companion automation for the `off` state that selects `available`.

## Meeting reminder

```yaml
alias: BUSY Bar - meeting reminder
triggers:
  - trigger: calendar
    entity_id: calendar.personal
    event: start
    offset: "-00:05:00"
actions:
  - action: busybar.show_message
    data:
      device_id: YOUR_DEVICE_ID
      message: "NEXT: {{ trigger.calendar_event.summary }}"
      color: [255, 255, 255]
      background: [8, 47, 73]
      led_color: [14, 165, 233]
      duration: 30
```

## Appliance progress

```yaml
alias: BUSY Bar - washer progress
triggers:
  - trigger: state
    entity_id: sensor.washer_progress
actions:
  - action: busybar.show_progress
    data:
      device_id: YOUR_DEVICE_ID
      value: "{{ trigger.to_state.state | float(0) }}"
      label: WASHER
      color: [34, 211, 238]
      duration: 60
```

## Emergency interruption

Priority 100 intentionally overrides a focus session. Reserve it for things that truly deserve interruption.

```yaml
alias: BUSY Bar - smoke alarm
triggers:
  - trigger: state
    entity_id: binary_sensor.smoke_alarm
    to: "on"
actions:
  - action: busybar.show_message
    data:
      device_id: YOUR_DEVICE_ID
      message: SMOKE ALARM
      color: [255, 255, 255]
      background: [185, 28, 28]
      led_color: [255, 0, 0]
      priority: 100
      duration: 0
```

## Focus from an NFC tag

```yaml
alias: BUSY Bar - desk focus tag
triggers:
  - trigger: tag
    tag_id: YOUR_TAG_ID
actions:
  - action: busybar.start_focus
    data:
      device_id: YOUR_DEVICE_ID
      minutes: 25
      theme: on_air
```

