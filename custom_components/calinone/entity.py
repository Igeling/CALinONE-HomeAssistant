"""Gemeinsame Entity-Basis für CALinONE."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .coordinator import CalinoneCoordinator


class CalinoneEntity(Entity):
    """Basisklasse: hängt am Coordinator und am gemeinsamen „Gerät" CALinONE.

    Die entity_id wird explizit gesetzt (sensor.calinone_current_shift usw.),
    damit sie stabil und sprachunabhängig ist — Anzeigenamen kommen aus den
    translations und folgen der HA-Sprache.
    """

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CalinoneCoordinator,
        key: str,
        platform: str,
    ) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_translation_key = key
        self.entity_id = f"{platform}.calinone_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="CALinONE",
            manufacturer="Igeling",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self) -> bool:
        # Verfügbar, sobald die App mindestens einmal gepusht hat.
        return self.coordinator.has_data
