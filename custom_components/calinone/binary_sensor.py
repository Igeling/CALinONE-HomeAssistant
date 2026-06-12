"""Binärsensoren: Arbeitstag und Urlaub heute."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CalinoneCoordinator
from .entity import CalinoneEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CalinoneCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [WorkDaySensor(coordinator), VacationTodaySensor(coordinator)]
    )


class WorkDaySensor(CalinoneEntity, BinarySensorEntity):
    _attr_icon = "mdi:briefcase"

    def __init__(self, coordinator: CalinoneCoordinator) -> None:
        super().__init__(coordinator, "work_day", "binary_sensor")

    @property
    def is_on(self) -> bool:
        return self.coordinator.snapshot()["work_day"]


class VacationTodaySensor(CalinoneEntity, BinarySensorEntity):
    _attr_icon = "mdi:palm-tree"

    def __init__(self, coordinator: CalinoneCoordinator) -> None:
        super().__init__(coordinator, "vacation_today", "binary_sensor")

    @property
    def is_on(self) -> bool:
        return self.coordinator.snapshot()["vacation_today"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"leave_type": self.coordinator.snapshot()["leave_type"]}
