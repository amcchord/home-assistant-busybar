# Automation recipes

The repository ships with 13 blueprints under `blueprints/automation/busybar`. Import the desired raw GitHub URL in Home Assistant's blueprint UI, choose your Bar and source entity, and the automation is ready. HACS integration installs are intentionally limited to `custom_components`, so blueprint import remains an explicit one-time step. The blueprints cover calendars, appliances, progress, physical focus mode, doorbells, updates, arrivals, weather, air quality, bedtime, deliveries, daily streaks, and safety alarms.

The examples below use `YOUR_DEVICE_ID`. Custom actions accept one ID or a list of IDs.

## Mirror call state

```yaml
alias: BUSY Bar — on a call
triggers:
  - trigger: state
    entity_id: binary_sensor.microphone_in_use
actions:
  - choose:
      - conditions: "{{ trigger.to_state.state == 'on' }}"
        sequence:
          - action: select.select_option
            target:
              entity_id: select.studio_bar_status_scene
            data:
              option: on_air
    default:
      - action: select.select_option
        target:
          entity_id: select.studio_bar_status_scene
        data:
          option: available
```

## A temporary calendar countdown

```yaml
alias: BUSY Bar — next meeting
triggers:
  - trigger: calendar
    entity_id: calendar.work
    event: start
    offset: "-00:05:00"
actions:
  - action: busybar.show_widget
    data:
      device_id: YOUR_DEVICE_ID
      widget: countdown
      title: "{{ trigger.calendar_event.summary }}"
      timestamp: "{{ trigger.calendar_event.start }}"
      color: [56, 189, 248]
      duration: 300
      priority: 60
      restore: true
```

The previous Home Assistant layer is restored after five minutes. An active focus session at priority 90 still wins.

## A stable progress layer

Use a `layer_id` to update one long-lived widget as often as the source changes:

```yaml
alias: BUSY Bar — printer progress
triggers:
  - trigger: state
    entity_id: sensor.printer_progress
conditions:
  - condition: template
    value_template: "{{ trigger.to_state.state | float(none) is not none }}"
actions:
  - action: busybar.show_widget
    data:
      device_id: YOUR_DEVICE_ID
      widget: progress
      title: 3D PRINT
      value: "{{ trigger.to_state.state | round(0) }}%"
      progress: "{{ trigger.to_state.state | float(0) }}"
      color: [34, 211, 238]
      duration: 0
      priority: 40
      layer_id: printer-progress
```

Call `busybar.clear_display` when the job ends, or replace this with a completion preset.

## Household presets

```yaml
alias: BUSY Bar — dryer complete
triggers:
  - trigger: state
    entity_id: binary_sensor.dryer_running
    from: "on"
    to: "off"
actions:
  - action: busybar.play_preset
    data:
      device_id: YOUR_DEVICE_ID
      preset: laundry_done
      message: DRYER DONE
```

Preset names are `someone_is_here`, `package_delivered`, `laundry_done`, `dinner_ready`, `meeting_soon`, `weather_warning`, `air_quality_warning`, `alarm`, `welcome_home`, `bedtime`, `chore_complete`, `focus_break`, `goal_scored`, `print_complete`, and `celebration`.

## Use the physical controls

Device triggers are easiest to choose in the visual automation editor. The same events are also fired on the Home Assistant bus as `busybar_event`:

```yaml
alias: BUSY Bar — encoder dims the office
triggers:
  - trigger: event
    event_type: busybar_event
    event_data:
      source: encoder
      type: counterclockwise
actions:
  - action: light.turn_on
    target:
      entity_id: light.office
    data:
      brightness_step_pct: -10
```

Event data includes `entry_id`, `category`, `type`, and `source`, plus details such as `button`, `action`, `position`, `direction`, `delta`, `timer_type`, `paused`, `remaining_seconds`, and `current_interval` when relevant.

## Coordinate multiple Bars

```yaml
action: busybar.play_effect
data:
  device_id:
    - DEVICE_ID_OFFICE
    - DEVICE_ID_KITCHEN
    - DEVICE_ID_WORKSHOP
  effect: fireworks
  message: WE DID IT!
  duration: 10
```

The integration starts targeted coordinators concurrently, producing a close visual start without routing through a cloud broker.

## Emergency interruption

Priority 100 intentionally overrides a focus session. Reserve it for safety-critical alerts.

```yaml
alias: BUSY Bar — smoke alarm
triggers:
  - trigger: state
    entity_id: binary_sensor.smoke_alarm
    to: "on"
actions:
  - action: busybar.play_preset
    data:
      device_id: YOUR_DEVICE_ID
      preset: alarm
      message: SMOKE ALARM
      priority: 100
      duration: 20
```

## Start focus from NFC

```yaml
alias: BUSY Bar — desk focus tag
triggers:
  - trigger: tag
    tag_id: YOUR_TAG_ID
actions:
  - action: busybar.start_focus
    data:
      device_id: YOUR_DEVICE_ID
      minutes: 25
      theme: on_air
      trigger_smart_home: true
```

This starts a one-off timer without changing either physical switch profile.
