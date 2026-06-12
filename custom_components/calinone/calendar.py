"""Kalender-Entity: Schichten, Urlaube und Termine aus dem App-Schedule."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SHIFT_SUMMARY_SEPARATOR
from .coordinator import CalinoneCoordinator, shift_times
from .entity import CalinoneEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CalinoneCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CalinoneCalendar(coordinator)])


def _events_for_day(d: date, day: dict[str, Any]) -> list[CalendarEvent]:
    """Alle Kalender-Events eines Tages bauen.

    Schichten mit Zeiten werden zeitgebunden angelegt (Nachtschicht endet am
    Folgetag), alles andere ganztägig — gleiche Darstellung wie der frühere
    Sync ("F – Frühschicht", "🏖 Urlaub", "📌 14:00 Termin").
    """
    events: list[CalendarEvent] = []

    for shift in day.get("sh") or []:
        summary = (
            f"{shift.get('s', '?')}{SHIFT_SUMMARY_SEPARATOR}{shift.get('n', '?')}"
        )
        times = shift_times(shift)
        if times is not None:
            start_t, end_t = times
            start = dt_util.as_local(
                datetime.combine(d, start_t, tzinfo=dt_util.get_default_time_zone())
            )
            end = dt_util.as_local(
                datetime.combine(d, end_t, tzinfo=dt_util.get_default_time_zone())
            )
            if end <= start:
                end += timedelta(days=1)  # Nachtschicht über Mitternacht
            events.append(CalendarEvent(summary=summary, start=start, end=end))
        else:
            events.append(
                CalendarEvent(summary=summary, start=d, end=d + timedelta(days=1))
            )

    for leave in day.get("lv") or []:
        events.append(
            CalendarEvent(
                summary=f"\U0001f3d6 {leave.get('n', '?')}",
                start=d,
                end=d + timedelta(days=1),
            )
        )

    for appointment in day.get("ap") or []:
        title = appointment.get("t") or "Termin"
        location = appointment.get("l")
        hour = appointment.get("h")
        if hour is not None:
            minute = appointment.get("m") or 0
            start = dt_util.as_local(
                datetime.combine(
                    d,
                    datetime.min.time().replace(hour=hour, minute=minute),
                    tzinfo=dt_util.get_default_time_zone(),
                )
            )
            events.append(
                CalendarEvent(
                    summary=f"\U0001f4cc {hour:02d}:{minute:02d} {title}",
                    start=start,
                    end=start + timedelta(hours=1),
                    location=location,
                )
            )
        else:
            events.append(
                CalendarEvent(
                    summary=f"\U0001f4cc {title}",
                    start=d,
                    end=d + timedelta(days=1),
                    location=location,
                )
            )

    return events


class CalinoneCalendar(CalinoneEntity, CalendarEntity):
    """calendar.calinone — der komplette Plan als Kalender."""

    def __init__(self, coordinator: CalinoneCoordinator) -> None:
        super().__init__(coordinator, "calendar", "calendar")
        # Bewusst ohne Suffix: calendar.calinone
        self.entity_id = "calendar.calinone"

    @property
    def event(self) -> CalendarEvent | None:
        """Aktives oder nächstes Event (bestimmt den on/off-Zustand)."""
        now = dt_util.now()
        today = now.date()
        upcoming: CalendarEvent | None = None
        for d, day in self.coordinator.days_in_range(
            today, today + timedelta(days=60)
        ):
            for ev in _events_for_day(d, day):
                start = _as_datetime(ev.start)
                end = _as_datetime(ev.end)
                if end <= now:
                    continue
                if start <= now:
                    return ev  # läuft gerade
                if upcoming is None or start < _as_datetime(upcoming.start):
                    upcoming = ev
            if upcoming is not None and d > today:
                break
        return upcoming

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []
        # Einen Tag Vorlauf, damit Nachtschichten des Vortags erfasst werden.
        for d, day in self.coordinator.days_in_range(
            start_date.date() - timedelta(days=1), end_date.date()
        ):
            for ev in _events_for_day(d, day):
                if _as_datetime(ev.end) > start_date and _as_datetime(
                    ev.start
                ) < end_date:
                    events.append(ev)
        return events


def _as_datetime(value: datetime | date) -> datetime:
    """date/datetime vereinheitlichen (ganztägige Events sind dates)."""
    if isinstance(value, datetime):
        return value
    return dt_util.start_of_local_day(value)
