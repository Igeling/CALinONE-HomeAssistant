# CALinONE für Home Assistant

[![Validate](https://github.com/Igeling/CALinONE-HomeAssistant/actions/workflows/validate.yml/badge.svg)](https://github.com/Igeling/CALinONE-HomeAssistant/actions/workflows/validate.yml)

Empfängt den Schichtplan der [CALinONE-App](https://cal-in-one.app) und stellt ihn
als Kalender und Sensoren in Home Assistant bereit.

## Installation

### Über HACS (empfohlen)

Der Button öffnet das Repository direkt in HACS auf **deiner** Home-Assistant-Instanz:

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Igeling&repository=CALinONE-HomeAssistant&category=integration)

Oder manuell:

1. HACS → drei Punkte (oben rechts) → **Benutzerdefinierte Repositories**
2. Repository-URL eintragen, Typ **Integration**, hinzufügen
3. „CALinONE" in HACS suchen und installieren
4. Home Assistant neu starten

### Manuell

1. Den Ordner `custom_components/calinone` in dein HA-Konfigurationsverzeichnis
   kopieren (`<config>/custom_components/calinone`)
2. Home Assistant neu starten

## Einrichtung

Der Button startet den Einrichtungs-Dialog direkt in deinem Home Assistant:

[![Open your Home Assistant instance and start setting up this integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=calinone)

Oder manuell:

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen** → „CALinONE"
2. Den Dialog bestätigen — Home Assistant zeigt dir eine **Webhook-URL** an
3. Diese URL in der CALinONE-App eintragen: **Einstellungen → Home Assistant**
4. In der App auf **„Verbindung testen"** tippen — fertig

Die App sendet ab jetzt bei jeder Änderung deinen Plan (rollierendes Fenster:
3 Monate zurück bis 12 Monate voraus). Die Integration berechnet alle Werte
selbst und funktioniert auch, wenn die App geschlossen ist: Werte überleben
HA-Neustarts und rollen um Mitternacht automatisch auf den neuen Tag.

## Entities

| Entity-ID | Was sie zeigt |
|-----------|---------------|
| `calendar.calinone` | Alle Schichten, Urlaube und Termine als Kalender |
| `sensor.calinone_current_shift` | Heutige Schicht (Name) oder `off` |
| `sensor.calinone_shift_start` | Schichtbeginn heute, z. B. `06:00` (sonst `-`) |
| `sensor.calinone_shift_end` | Schichtende heute, z. B. `14:00` (sonst `-`) |
| `sensor.calinone_shift_duration` | Schichtdauer heute in Stunden (Nachtschichten korrekt) |
| `sensor.calinone_next_shift` | Schicht/Urlaub **morgen** (Name) oder `off` |
| `sensor.calinone_next_appointment` | Nächster Termin **heute** (Titel) oder `off` |
| `sensor.calinone_appointment_category` | Kategorie dieses Termins (`-` = ohne, `off` = kein Termin) |
| `binary_sensor.calinone_work_day` | `on` = heute Arbeitstag (an Urlaubstagen `off`) |
| `binary_sensor.calinone_vacation_today` | `on` = heute Urlaub/Abwesenheit |

Nach jedem Push der App feuert die Integration zusätzlich das Bus-Event
**`calinone_updated`** — nützlich als Trigger für eigene Automatisierungen.

## Beispiel-Automatisierung

```yaml
automation:
  - alias: "Heizung vor Schichtbeginn"
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
          entity_id: climate.wohnzimmer
        data:
          temperature: 22
```

## Sicherheit

- Die Webhook-URL ist das einzige Geheimnis (wie bei der offiziellen HA Companion
  App). Behandle sie wie ein Passwort.
- Der Webhook akzeptiert nur `POST` mit CALinONE-Daten; er kann nichts in
  Home Assistant steuern oder auslesen.

## Hilfe

Vollständige Anleitung: https://cal-in-one.app/homeassistant
