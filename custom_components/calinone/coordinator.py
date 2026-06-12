"""Datenhaltung und Tageslogik für CALinONE.

Hält den von der App gepushten Schedule (rollierendes Fenster, JSON-Format
v1 der App — kompakte Keys: days/d/sh/lv/ap), persistiert ihn über
helpers.storage (überlebt HA-Neustarts) und berechnet die abgeleiteten
Tageswerte. Entities abonnieren sich als Listener; ein Timer kurz nach
Mitternacht sorgt für den Tageswechsel.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_time_change,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, EVENT_UPDATED, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


def _day_date(day: dict[str, Any]) -> date | None:
    """Datum eines Tages-Eintrags ('d': ISO-String) als date."""
    raw = day.get("d")
    if not isinstance(raw, str) or len(raw) < 10:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def shift_times(shift: dict[str, Any]) -> tuple[time, time] | None:
    """Start-/Endzeit einer Schicht, falls beide vorhanden sind."""
    sh, eh = shift.get("sh"), shift.get("eh")
    if sh is None or eh is None:
        return None
    return (
        time(hour=sh, minute=shift.get("sm") or 0),
        time(hour=eh, minute=shift.get("em") or 0),
    )


def shift_duration_hours(shift: dict[str, Any]) -> float:
    """Schichtdauer in Stunden; Nachtschichten über Mitternacht korrekt."""
    times = shift_times(shift)
    if times is None:
        return 0.0
    start, end = times
    minutes = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
    if minutes < 0:
        minutes += 24 * 60
    return round(minutes / 60.0, 1)


def _fmt(t: time) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"


class CalinoneCoordinator:
    """Hält den Schedule und benachrichtigt Entities bei Änderungen."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._schedule: dict[str, Any] = {}
        self._by_date: dict[date, dict[str, Any]] = {}
        self._listeners: list[Callable[[], None]] = []
        self._unsub_midnight: Callable[[], None] | None = None
        self._unsub_appointment: Callable[[], None] | None = None

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def async_load(self) -> None:
        """Persistierten Schedule laden (nach HA-Neustart)."""
        data = await self._store.async_load()
        if isinstance(data, dict):
            self._schedule = data
            self._rebuild_index()

    @callback
    def async_start(self) -> None:
        """Mitternachts-Timer starten (Tageswechsel der abgeleiteten Werte)."""
        self._unsub_midnight = async_track_time_change(
            self.hass, self._handle_midnight, hour=0, minute=0, second=30
        )

    @callback
    def async_stop(self) -> None:
        if self._unsub_midnight is not None:
            self._unsub_midnight()
            self._unsub_midnight = None
        if self._unsub_appointment is not None:
            self._unsub_appointment()
            self._unsub_appointment = None

    async def _handle_midnight(self, _now: datetime) -> None:
        self.async_notify_listeners()

    # ── Schedule-Updates (vom Webhook) ───────────────────────────────────

    async def async_set_schedule(self, schedule: dict[str, Any]) -> None:
        """Neuen Schedule aus der App übernehmen, speichern, alle informieren."""
        self._schedule = schedule
        self._rebuild_index()
        await self._store.async_save(schedule)
        self.async_notify_listeners()
        self.hass.bus.async_fire(EVENT_UPDATED, {"days": len(self._by_date)})

    def _rebuild_index(self) -> None:
        self._by_date = {}
        for day in self._schedule.get("days") or []:
            if not isinstance(day, dict):
                continue
            d = _day_date(day)
            if d is not None:
                self._by_date[d] = day

    # ── Listener (Entities) ──────────────────────────────────────────────

    @callback
    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update)

        def _remove() -> None:
            if update in self._listeners:
                self._listeners.remove(update)

        return _remove

    @callback
    def async_notify_listeners(self) -> None:
        for update in list(self._listeners):
            update()
        self._schedule_appointment_rollover()

    @callback
    def _schedule_appointment_rollover(self) -> None:
        """Timer auf den nächsten Terminbeginn heute setzen.

        Kurz nach Beginn eines Termins rückt `next_appointment` automatisch
        zum folgenden Termin weiter — dafür braucht es einen eigenen Tick
        (die übrigen Werte ändern sich nur per Push/Mitternacht).
        """
        if self._unsub_appointment is not None:
            self._unsub_appointment()
            self._unsub_appointment = None

        now = dt_util.now()
        next_tick: datetime | None = None
        for appointment in self.day(now.date()).get("ap") or []:
            hour = appointment.get("h")
            if hour is None:
                continue
            tick = now.replace(
                hour=hour,
                minute=appointment.get("m") or 0,
                second=0,
                microsecond=0,
            ) + timedelta(minutes=1)
            if tick > now and (next_tick is None or tick < next_tick):
                next_tick = tick

        if next_tick is not None:
            self._unsub_appointment = async_track_point_in_time(
                self.hass, self._handle_appointment_tick, next_tick
            )

    async def _handle_appointment_tick(self, _now: datetime) -> None:
        self.async_notify_listeners()

    # ── Abfragen ─────────────────────────────────────────────────────────

    @property
    def has_data(self) -> bool:
        return bool(self._by_date)

    @property
    def updated_at(self) -> str | None:
        value = self._schedule.get("u")
        return value if isinstance(value, str) else None

    def day(self, d: date) -> dict[str, Any]:
        return self._by_date.get(d) or {}

    def days_in_range(self, start: date, end: date) -> list[tuple[date, dict[str, Any]]]:
        """Alle Tage mit Einträgen in [start, end] (beide inklusiv)."""
        return sorted(
            (d, day) for d, day in self._by_date.items() if start <= d <= end
        )

    # ── Abgeleitete Tageswerte ───────────────────────────────────────────

    def _first_shift(self, d: date) -> dict[str, Any] | None:
        shifts = self.day(d).get("sh") or []
        return shifts[0] if shifts else None

    def _first_leave(self, d: date) -> dict[str, Any] | None:
        leaves = self.day(d).get("lv") or []
        return leaves[0] if leaves else None

    def _next_appointment(self) -> dict[str, Any] | None:
        """Nächster Termin heute.

        Bevorzugt den frühesten zeitgebundenen Termin, der noch nicht
        begonnen hat; gibt es keinen (mehr), fällt die Auswahl auf einen
        ganztägigen Termin des Tages. None, wenn heute nichts (mehr) ansteht.
        """
        now = dt_util.now()
        timed: list[tuple[datetime, dict[str, Any]]] = []
        untimed: list[dict[str, Any]] = []
        for appointment in self.day(now.date()).get("ap") or []:
            hour = appointment.get("h")
            if hour is None:
                untimed.append(appointment)
                continue
            start = now.replace(
                hour=hour,
                minute=appointment.get("m") or 0,
                second=0,
                microsecond=0,
            )
            timed.append((start, appointment))
        timed.sort(key=lambda item: item[0])
        for start, appointment in timed:
            if start >= now:
                return appointment
        return untimed[0] if untimed else None

    def snapshot(self) -> dict[str, Any]:
        """Alle abgeleiteten Werte für heute/morgen auf einen Blick.

        Semantik wie in der App: Urlaub hat Vorrang — an einem Urlaubstag ist
        work_day aus und current_shift 'off'.
        """
        # HA-Zeitzone, nicht Server-Zeitzone.
        today = dt_util.now().date()
        tomorrow = today + timedelta(days=1)

        shift = self._first_shift(today)
        leave = self._first_leave(today)
        is_vacation = leave is not None
        is_work_day = shift is not None and not is_vacation

        times = shift_times(shift) if shift else None
        start_str = _fmt(times[0]) if times else "-"
        end_str = _fmt(times[1]) if times else "-"
        crosses_midnight = times is not None and (
            (times[1].hour, times[1].minute) < (times[0].hour, times[0].minute)
        )

        shift_tomorrow = self._first_shift(tomorrow)
        leave_tomorrow = self._first_leave(tomorrow)
        if leave_tomorrow is not None:
            next_state = leave_tomorrow.get("n") or "off"
        elif shift_tomorrow is not None:
            next_state = shift_tomorrow.get("n") or "off"
        else:
            next_state = "off"

        # Termine: nächster Termin heute + dessen Kategorie.
        appointment = self._next_appointment()
        appointment_hour = (appointment or {}).get("h")
        appointment_time = (
            f"{appointment_hour:02d}:{(appointment or {}).get('m') or 0:02d}"
            if appointment_hour is not None
            else "-"
        )
        category_color = (appointment or {}).get("cc")

        return {
            "current_shift": "off"
            if (is_vacation or shift is None)
            else (shift.get("n") or "Unknown"),
            "current_shift_short": (shift or {}).get("s"),
            "crosses_midnight": crosses_midnight,
            "shift_start": start_str,
            "shift_end": end_str,
            "shift_duration": shift_duration_hours(shift) if shift else 0.0,
            "next_shift": next_state,
            "next_shift_short": (shift_tomorrow or {}).get("s"),
            "next_is_leave": leave_tomorrow is not None,
            "work_day": is_work_day,
            "vacation_today": is_vacation,
            "leave_type": (leave or {}).get("n"),
            "appointment": "off"
            if appointment is None
            else (appointment.get("t") or "Termin"),
            "appointment_time": appointment_time,
            "appointment_location": (appointment or {}).get("l"),
            "appointment_category": (appointment or {}).get("cn"),
            "appointment_category_state": "off"
            if appointment is None
            else (appointment.get("cn") or "-"),
            "appointment_category_color": f"#{category_color & 0xFFFFFF:06X}"
            if isinstance(category_color, int)
            else None,
            "appointments_today": len(
                self.day(today).get("ap") or []
            ),
        }
