"""CALinONE – empfängt den Schichtplan der CALinONE-App per Webhook.

Sicherheitsmodell: Die App authentifiziert sich NICHT mit einem
Long-Lived-Token, sondern postet ausschließlich an die Webhook-URL dieser
Integration (die Webhook-ID ist das Geheimnis, wie bei der HA Companion
App). Damit hat die App keinerlei Zugriff auf den Rest von Home Assistant.
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from json import JSONDecodeError
from typing import Any

from aiohttp import web

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS, SCHEMA_VERSION
from .coordinator import CalinoneCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration für einen Config-Entry starten."""
    coordinator = CalinoneCoordinator(hass, entry)
    await coordinator.async_load()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    webhook.async_register(
        hass,
        DOMAIN,
        "CALinONE",
        entry.data[CONF_WEBHOOK_ID],
        _make_webhook_handler(coordinator),
        allowed_methods=["POST"],
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration sauber entladen."""
    webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: CalinoneCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator.async_stop()
    return unload_ok


def _make_webhook_handler(coordinator: CalinoneCoordinator):
    """Webhook-Handler mit gebundenem Coordinator bauen."""

    async def handle_webhook(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        try:
            payload: Any = await request.json()
        except (JSONDecodeError, ValueError):
            return web.json_response(
                {"ok": False, "error": "invalid_json"},
                status=HTTPStatus.BAD_REQUEST,
            )

        if not isinstance(payload, dict):
            return web.json_response(
                {"ok": False, "error": "invalid_payload"},
                status=HTTPStatus.BAD_REQUEST,
            )

        msg_type = payload.get("type")

        # Verbindungstest aus der App.
        if msg_type == "ping":
            return web.json_response(
                {"ok": True, "name": "CALinONE", "schema": SCHEMA_VERSION}
            )

        # Voller Schedule-Push (rollierendes Fenster).
        if msg_type == "schedule":
            schedule = payload.get("schedule")
            if not isinstance(schedule, dict) or "days" not in schedule:
                return web.json_response(
                    {"ok": False, "error": "invalid_schedule"},
                    status=HTTPStatus.BAD_REQUEST,
                )
            await coordinator.async_set_schedule(schedule)
            return web.json_response({"ok": True})

        return web.json_response(
            {"ok": False, "error": "unknown_type"},
            status=HTTPStatus.BAD_REQUEST,
        )

    return handle_webhook
