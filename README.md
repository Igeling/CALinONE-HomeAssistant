# CALinONE for Home Assistant

[![Validate](https://github.com/Igeling/CALinONE-HomeAssistant/actions/workflows/validate.yml/badge.svg)](https://github.com/Igeling/CALinONE-HomeAssistant/actions/workflows/validate.yml)

Receives the schedule from the [CALinONE app](https://cal-in-one.app) and exposes
it as a calendar and sensors in Home Assistant.

The app only sends data to this integration's webhook — it never gets access to
anything else in your Home Assistant. No long-lived access token, no admin
account required.

## Installation

### Via HACS (recommended)

The button opens this repository directly in HACS on **your** Home Assistant instance:

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Igeling&repository=CALinONE-HomeAssistant&category=integration)

Or manually:

1. HACS → three dots (top right) → **Custom repositories**
2. Add the repository URL, type **Integration**
3. Search for "CALinONE" in HACS and install it
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/calinone` folder into your Home Assistant
   configuration directory (`<config>/custom_components/calinone`)
2. Restart Home Assistant

## Setup

The button starts the setup dialog directly in your Home Assistant:

[![Open your Home Assistant instance and start setting up this integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=calinone)

Or manually:

1. **Settings → Devices & Services → Add Integration** → "CALinONE"
2. Confirm the dialog — Home Assistant shows you a **webhook URL**
3. Enter this URL in the CALinONE app: **Settings → Home Assistant**
4. Tap **"Test connection"** in the app — done

From now on the app sends your schedule on every change (rolling window:
3 months back to 12 months ahead). The integration computes all values itself
and keeps working when the app is closed: values survive Home Assistant
restarts and roll over to the new day at midnight automatically.

## Entities

| Entity ID | What it shows |
|-----------|---------------|
| `calendar.calinone` | All shifts, vacations and appointments as a calendar |
| `sensor.calinone_current_shift` | Today's shift (name) or `off` |
| `sensor.calinone_shift_start` | Shift start today, e.g. `06:00` (else `-`) |
| `sensor.calinone_shift_end` | Shift end today, e.g. `14:00` (else `-`) |
| `sensor.calinone_shift_duration` | Shift duration today in hours (night shifts handled correctly) |
| `sensor.calinone_next_shift` | Shift/vacation **tomorrow** (name) or `off` |
| `sensor.calinone_next_appointment` | Next appointment **today** (title) or `off` |
| `sensor.calinone_appointment_category` | Category of that appointment (`-` = none, `off` = no appointment) |
| `binary_sensor.calinone_work_day` | `on` = work day today (`off` on vacation days) |
| `binary_sensor.calinone_vacation_today` | `on` = vacation/absence today |

Entity display names follow your Home Assistant language (English and German
included). After each push from the app the integration also fires the bus
event **`calinone_updated`** — useful as a trigger for your own automations.

## Example automation

```yaml
automation:
  - alias: "Heating before shift start"
    trigger:
      - platform: time
        at: "05:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.calinone_work_day
        state: "on"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room
        data:
          temperature: 22
```

## Security

- The webhook URL is the only secret (same principle as the official Home
  Assistant Companion App). Treat it like a password.
- The webhook only accepts `POST` requests with CALinONE schedule data; it
  cannot control or read anything in Home Assistant.
- If needed, remove and re-add the integration — a new webhook URL is created
  and the old one becomes invalid.

## Help

Full setup guide: https://cal-in-one.app/homeassistant
