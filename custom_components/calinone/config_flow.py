"""Config-Flow für CALinONE.

Nutzt den HA-Standard-Webhook-Flow (wie IFTTT & Co.): Beim Hinzufügen wird
eine Webhook-ID erzeugt und die fertige Webhook-URL im Abschluss-Dialog
angezeigt — diese URL trägt der User in der CALinONE-App ein. Mehr braucht
es nicht: kein Token, keine Zugangsdaten.
"""

from homeassistant.helpers import config_entry_flow

from .const import DOMAIN

config_entry_flow.register_webhook_flow(
    DOMAIN,
    "CALinONE",
    {"docs_url": "https://cal-in-one.app/homeassistant"},
    allow_multiple=False,
)
