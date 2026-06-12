"""Sensoren: heutige Schicht, Beginn/Ende/Dauer, nächste Schicht."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
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
        [
            CurrentShiftSensor(coordinator),
            ShiftStartSensor(coordinator),
            ShiftEndSensor(coordinator),
            ShiftDurationSensor(coordinator),
            NextShiftSensor(coordinator),
            NextAppointmentSensor(coordinator),
            AppointmentCategorySensor(coordinator),
        ]
    )


class _Sensor(CalinoneEntity, SensorEntity):
    def __init__(self, coordinator: CalinoneCoordinator, key: str) -> None:
        super().__init__(coordinator, key, "sensor")

    @property
    def _snap(self) -> dict[str, Any]:
        return self.coordinator.snapshot()


class CurrentShiftSensor(_Sensor):
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: CalinoneCoordinator) -> None:
        super().__init__(coordinator, "current_shift")

    @property
    def native_value(self) -> str:
        return self._snap["current_shift"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snap = self._snap
        return {
            "short_name": snap["current_shift_short"],
            "start_time": snap["shift_start"],
            "end_time": snap["shift_end"],
            "crosses_midnight": snap["crosses_midnight"],
            "updated_at": self.coordinator.updated_at,
        }


class ShiftStartSensor(_Sensor):
    _attr_icon = "mdi:clock-start"

    def __init__(self, coordinator: CalinoneCoordinator) -> None:
        super().__init__(coordinator, "shift_start")

    @property
    def native_value(self) -> str:
        return self._snap["shift_start"]


class ShiftEndSensor(_Sensor):
    _attr_icon = "mdi:clock-end"

    def __init__(self, coordinator: CalinoneCoordinator) -> None:
        super().__init__(coordinator, "shift_end")

    @property
    def native_value(self) -> str:
        return self._snap["shift_end"]


class ShiftDurationSensor(_Sensor):
    _attr_icon = "mdi:timer-outline"
    _attr_native_unit_of_measurement = "h"
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: CalinoneCoordinator) -> None:
        super().__init__(coordinator, "shift_duration")

    @property
    def native_value(self) -> float:
        return self._snap["shift_duration"]


class NextShiftSensor(_Sensor):
    _attr_icon = "mdi:calendar-today"

    def __init__(self, coordinator: CalinoneCoordinator) -> None:
        super().__init__(coordinator, "next_shift")

    @property
    def native_value(self) -> str:
        return self._snap["next_shift"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snap = self._snap
        return {
            "short_name": snap["next_shift_short"],
            "is_leave": snap["next_is_leave"],
        }


class NextAppointmentSensor(_Sensor):
    """Nächster Termin heute (Titel); rückt nach Terminbeginn automatisch
    zum folgenden Termin weiter, sonst 'off'."""

    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: CalinoneCoordinator) -> None:
        super().__init__(coordinator, "next_appointment")

    @property
    def native_value(self) -> str:
        return self._snap["appointment"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snap = self._snap
        return {
            "time": snap["appointment_time"],
            "location": snap["appointment_location"],
            "category": snap["appointment_category"],
            "appointments_today": snap["appointments_today"],
        }


class AppointmentCategorySensor(_Sensor):
    """Kategorie des nächsten Termins heute ('-' = Termin ohne Kategorie,
    'off' = kein Termin)."""

    _attr_icon = "mdi:tag-outline"

    def __init__(self, coordinator: CalinoneCoordinator) -> None:
        super().__init__(coordinator, "appointment_category")

    @property
    def native_value(self) -> str:
        return self._snap["appointment_category_state"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snap = self._snap
        return {
            "color": snap["appointment_category_color"],
            "appointment": snap["appointment"],
        }
