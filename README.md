The `humidifier_template` platform creates humidifier or dehumidifier devices that combine existing integrations and sensors into a single entity. It supports Jinja2 templates for reading state and runs scripts or service calls for each control command.

## Configuration

All configuration variables are optional unless noted. If a template is not defined for a given attribute the device will operate in **optimistic mode** for that attribute, meaning the state is assumed to have changed immediately when commanded.

### General Options

| Name         | Type     | Description                                                                                                                | Default                                              |
| ------------ | -------- | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `name`       | `string` | The name of the humidifier entity.                                                                                         | `"humidifier"`                                       |
| `unique_id`  | `string` | A [unique ID](https://developers.home-assistant.io/docs/entity_registry_index/#unique-id) for the entity.                  | Auto-generated from name                             |
| `type`       | `string` | Device class: `humidifier` or `dehumidifier`.                                                                              | `"dehumidifier"`                                     |
| `switch_id`  | `string` | Entity ID of a `switch` or `fan` to turn on/off when the humidifier is turned on/off. Mutually exclusive with `set_state_action`. | |
| `modes`      | `list`   | List of supported mode strings.                                                                                            | `["auto", "away", "normal"]`                         |
| `min_humidity` | `int`  | Minimum target humidity.                                                                                                   | `40`                                                 |
| `max_humidity` | `int`  | Maximum target humidity.                                                                                                   | `80`                                                 |

### Template Options

| Name                          | Type                                                                      | Description                                                                                                          |
| ----------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `state_template`              | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Returns the on/off state of the device. Must evaluate to `true`/`false` or `"on"`/`"off"`.                           |
| `current_humidity_template`   | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Returns the current humidity as an integer.                                                                          |
| `target_humidity_template`    | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Returns the target humidity as an integer.                                                                           |
| `mode_template`               | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Returns the current mode string.                                                                                     |
| `mode_list_template`          | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Returns a list of available modes. Overrides the static `modes` list when defined.                                   |
| `action_template`             | [`template`](https://www.home-assistant.io/docs/configuration/templating) | Returns the current action. Must evaluate to one of: `"off"`, `"idle"`, `"humidifying"`, `"drying"`.                |

### Action Options

Actions are [Home Assistant scripts](https://www.home-assistant.io/docs/scripts). Each action receives variables you can reference in templates inside the action.

| Name                          | Type                                                   | Available Variables                   | Description                                                    |
| ----------------------------- | ------------------------------------------------------ | ------------------------------------- | -------------------------------------------------------------- |
| `set_state_action`            | [`action`](https://www.home-assistant.io/docs/scripts) | `state` — `"on"` or `"off"`           | Runs when the humidifier is turned on or off. Mutually exclusive with `switch_id`. |
| `set_target_humidity_action`  | [`action`](https://www.home-assistant.io/docs/scripts) | `humidity` — integer target humidity  | Runs when the target humidity is changed.                      |
| `set_mode_action`             | [`action`](https://www.home-assistant.io/docs/scripts) | `mode` — the selected mode string     | Runs when the mode is changed.                                 |

### Device Info Options

The optional `device` block registers the entity under a specific device in the Home Assistant device registry.

| Name                | Type     | Description                                                              |
| ------------------- | -------- | ------------------------------------------------------------------------ |
| `identifiers`       | `list`   | One or more unique strings that identify the device. Required if `connections` is not set. |
| `connections`       | `list`   | List of `[type, value]` pairs (e.g., `[["mac", "aa:bb:cc:dd:ee:ff"]]`). Required if `identifiers` is not set. |
| `name`              | `string` | Name of the device.                                                      |
| `manufacturer`      | `string` | Manufacturer of the device.                                              |
| `model`             | `string` | Model of the device.                                                     |
| `hw_version`        | `string` | Hardware version string.                                                 |
| `sw_version`        | `string` | Software/firmware version string.                                        |
| `serial_number`     | `string` | Serial number of the device.                                             |
| `suggested_area`    | `string` | Suggested area for the device.                                           |
| `configuration_url` | `string` | URL to the device's configuration page.                                  |
| `via_device`        | `string` | Identifier of a parent device this device is connected through.          |

## Example Configuration

```yaml
humidifier:
  - platform: humidifier_template
    name: Bedroom Dehumidifier
    type: dehumidifier
    modes:
      - "auto"
      - "dry"
      - "comfort"
    min_humidity: 40
    max_humidity: 80

    # Read current humidity from a sensor
    current_humidity_template: "{{ states('sensor.bedroom_humidity') | int }}"

    # Read target humidity from an input number
    target_humidity_template: "{{ states('input_number.bedroom_target_humidity') | int }}"

    # Read mode from a fan entity
    mode_template: "{{ state_attr('fan.bedroom_dehumidifier', 'preset_mode') }}"

    # Read action from a sensor
    action_template: "{{ states('sensor.bedroom_dehumidifier_action') }}"

    # Turn on/off via a fan entity
    switch_id: fan.bedroom_dehumidifier

    # Set the mode via a service call — `mode` contains the selected mode string
    set_mode_action:
      - condition: state
        entity_id: input_boolean.enable_dehumidifier_controller
        state: "on"
      - service: fan.set_preset_mode
        target:
          entity_id: fan.bedroom_dehumidifier
        data:
          preset_mode: "{{ mode }}"

    # Set target humidity — `humidity` contains the integer target value
    set_target_humidity_action:
      - service: number.set_value
        target:
          entity_id: number.bedroom_dehumidifier_humidity
        data:
          value: "{{ humidity }}"
```

### Controlling on/off with a script instead of switch_id

Use `set_state_action` when you need custom logic for turning on and off. The `state` variable is `"on"` or `"off"`.

```yaml
humidifier:
  - platform: humidifier_template
    # ...
    set_state_action:
      - service: switch.turn_{{ state }}
        target:
          entity_id: switch.bedroom_dehumidifier_power
```

### Registering a device

```yaml
humidifier:
  - platform: humidifier_template
    name: Bedroom Dehumidifier
    # ...
    device:
      identifiers:
        - "bedroom_dehumidifier_001"
      manufacturer: "Acme"
      model: "DH-3000"
      sw_version: "1.2.3"
```

## Use Cases

- Combine multiple sensors and switches into a single humidifier entity.
- Control IR-based or ESPHome humidifiers/dehumidifiers via service calls.
- Bridge an existing fan or switch entity to the humidifier domain for a cleaner UI.
