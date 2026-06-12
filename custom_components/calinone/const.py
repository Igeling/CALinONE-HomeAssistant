"""Konstanten für die CALinONE-Integration."""

DOMAIN = "calinone"

# Version des Webhook-Protokolls zwischen App und Integration.
SCHEMA_VERSION = 1

# helpers.storage – der Schedule überlebt damit HA-Neustarts.
STORAGE_VERSION = 1

# Bus-Event nach jedem erfolgreichen Schedule-Push (für eigene Automatisierungen).
EVENT_UPDATED = "calinone_updated"

PLATFORMS = ["binary_sensor", "calendar", "sensor"]

# Trenner im Kalender-Event-Titel einer Schicht ("F – Frühschicht").
SHIFT_SUMMARY_SEPARATOR = " – "
