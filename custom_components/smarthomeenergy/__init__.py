"""SmartHomeEnergy - Smart battery charging based on electricity prices."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    CONF_PRICE_SENSOR,
    CONF_BATTERY_DEVICE_ID,
    CONF_DISCHARGE_POWER_ENTITY,
    CONF_CHEAPEST_CHARGE_HOURS,
    CONF_EXPENSIVE_DISCHARGE_HOURS,
    CONF_NIGHT_START,
    CONF_NIGHT_END,
    CONF_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    DEFAULT_PRICE_SENSOR,
    DEFAULT_DISCHARGE_POWER_ENTITY,
    DEFAULT_CHEAPEST_CHARGE_HOURS,
    DEFAULT_EXPENSIVE_DISCHARGE_HOURS,
    DEFAULT_NIGHT_START,
    DEFAULT_NIGHT_END,
    DEFAULT_CHARGE_POWER,
    DEFAULT_MAX_DISCHARGE_POWER,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SmartHomeEnergy from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = SmartChargeCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_start()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_stop()
    return unload_ok


class SmartChargeCoordinator:
    """Coordinator for smart battery charging/discharging."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self._unsub_timer = None
        self._cheapest_charge_hours: list[int] = []
        self._expensive_discharge_hours: list[int] = []
        self._all_prices: list[dict] = []
        self._current_mode = "idle"
        self._enabled = True
        self._listeners: list[callable] = []
        self._is_force_charging = False

    @property
    def price_sensor(self) -> str:
        return self.entry.data.get(CONF_PRICE_SENSOR, DEFAULT_PRICE_SENSOR)

    @property
    def battery_device_id(self) -> str:
        return self.entry.data.get(CONF_BATTERY_DEVICE_ID, "")

    @property
    def discharge_power_entity(self) -> str:
        return self.entry.data.get(CONF_DISCHARGE_POWER_ENTITY, DEFAULT_DISCHARGE_POWER_ENTITY)

    @property
    def num_charge_hours(self) -> int:
        return self.entry.data.get(CONF_CHEAPEST_CHARGE_HOURS, DEFAULT_CHEAPEST_CHARGE_HOURS)

    @property
    def num_discharge_hours(self) -> int:
        return self.entry.data.get(CONF_EXPENSIVE_DISCHARGE_HOURS, DEFAULT_EXPENSIVE_DISCHARGE_HOURS)

    @property
    def night_start(self) -> int:
        return self.entry.data.get(CONF_NIGHT_START, DEFAULT_NIGHT_START)

    @property
    def night_end(self) -> int:
        return self.entry.data.get(CONF_NIGHT_END, DEFAULT_NIGHT_END)

    @property
    def charge_power(self) -> int:
        return self.entry.data.get(CONF_CHARGE_POWER, DEFAULT_CHARGE_POWER)

    @property
    def max_discharge_power(self) -> int:
        return self.entry.data.get(CONF_MAX_DISCHARGE_POWER, DEFAULT_MAX_DISCHARGE_POWER)

    @property
    def cheapest_charge_hours(self) -> list[int]:
        return self._cheapest_charge_hours

    @property
    def expensive_discharge_hours(self) -> list[int]:
        return self._expensive_discharge_hours

    @property
    def all_prices(self) -> list[dict]:
        return self._all_prices

    @property
    def current_mode(self) -> str:
        return self._current_mode

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        self._notify_listeners()

    def add_listener(self, callback: callable) -> callable:
        self._listeners.append(callback)
        return lambda: self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        for listener in self._listeners:
            listener()

    async def async_start(self) -> None:
        await self._async_update()
        self._unsub_timer = async_track_time_interval(
            self.hass, self._async_update, timedelta(minutes=1)
        )

    async def async_stop(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

    def _is_in_night_period(self, hour: int) -> bool:
        """Check if hour is in night period."""
        if self.night_start <= self.night_end:
            return self.night_start <= hour < self.night_end
        else:
            return hour >= self.night_start or hour < self.night_end

    async def _async_update(self, now: datetime | None = None) -> None:
        """Update and control battery."""
        if not self._enabled:
            return

        try:
            state = self.hass.states.get(self.price_sensor)
            if state is None:
                _LOGGER.warning("Price sensor %s not found", self.price_sensor)
                return

            raw_today = state.attributes.get("raw_today", [])
            raw_tomorrow = state.attributes.get("raw_tomorrow", [])

            all_prices = []
            for price_data in raw_today + raw_tomorrow:
                if isinstance(price_data, dict):
                    hour_dt = price_data.get("hour")
                    price = price_data.get("price")
                    if hour_dt and price is not None:
                        if isinstance(hour_dt, str):
                            hour_dt = datetime.fromisoformat(hour_dt.replace("Z", "+00:00"))
                        all_prices.append({"hour": hour_dt, "price": price})

            self._all_prices = all_prices
            current_hour = datetime.now().hour
            old_mode = self._current_mode

            # Find cheapest night hours
            night_prices = [p for p in all_prices if self._is_in_night_period(p["hour"].hour)]
            night_prices.sort(key=lambda x: x["price"])
            self._cheapest_charge_hours = [p["hour"].hour for p in night_prices[:self.num_charge_hours]]

            # Find most expensive day hours (from night_end to midnight)
            day_prices = [p for p in all_prices if self.night_end <= p["hour"].hour < 24]
            day_prices.sort(key=lambda x: x["price"], reverse=True)
            self._expensive_discharge_hours = [p["hour"].hour for p in day_prices[:self.num_discharge_hours]]

            # Control logic
            is_night = self._is_in_night_period(current_hour)

            if is_night and current_hour in self._cheapest_charge_hours:
                if self._current_mode != "charging":
                    _LOGGER.info("Starting force charge - cheapest hour %s", current_hour)
                    await self._start_force_charge()
                self._current_mode = "charging"

            elif not is_night and current_hour in self._expensive_discharge_hours:
                if self._current_mode != "discharge_allowed":
                    _LOGGER.info("Allowing discharge - expensive hour %s", current_hour)
                    await self._stop_force_charge()
                    await self._set_discharge_power(self.max_discharge_power)
                self._current_mode = "discharge_allowed"

            else:
                if self._current_mode != "discharge_blocked":
                    _LOGGER.info("Blocking discharge - hour %s", current_hour)
                    await self._stop_force_charge()
                    await self._set_discharge_power(0)
                self._current_mode = "discharge_blocked"

            if old_mode != self._current_mode:
                self._notify_listeners()

        except Exception as e:
            _LOGGER.error("Error updating smart charge: %s", e)

    async def _start_force_charge(self) -> None:
        """Start force charging the battery."""
        if not self.battery_device_id:
            _LOGGER.warning("No battery device ID configured")
            return
        try:
            await self.hass.services.async_call(
                "huawei_solar",
                "forcible_charge",
                {
                    "device_id": self.battery_device_id,
                    "duration": 60,
                    "power": self.charge_power,
                }
            )
            self._is_force_charging = True
        except Exception as e:
            _LOGGER.error("Failed to start force charge: %s", e)

    async def _stop_force_charge(self) -> None:
        """Stop force charging."""
        if self._is_force_charging and self.battery_device_id:
            try:
                await self.hass.services.async_call(
                    "huawei_solar",
                    "stop_forcible_charge",
                    {"device_id": self.battery_device_id}
                )
                self._is_force_charging = False
            except Exception as e:
                _LOGGER.error("Failed to stop force charge: %s", e)

    async def _set_discharge_power(self, power: int) -> None:
        """Set maximum discharge power."""
        try:
            await self.hass.services.async_call(
                "number",
                "set_value",
                {
                    "entity_id": self.discharge_power_entity,
                    "value": power,
                }
            )
        except Exception as e:
            _LOGGER.error("Failed to set discharge power: %s", e)
