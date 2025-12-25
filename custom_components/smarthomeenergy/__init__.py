"""SmartHomeEnergy - Smart battery optimization based on electricity prices."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval, async_track_time_change

from .const import (
    DOMAIN,
    CONF_PRICE_SENSOR,
    CONF_BATTERY_DEVICE_ID,
    CONF_DISCHARGE_POWER_ENTITY,
    CONF_BATTERY_CAPACITY,
    CONF_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_BATTERY_EFFICIENCY,
    CONF_MIN_SOC,
    CONF_MAX_SOC,
    DEFAULT_PRICE_SENSOR,
    DEFAULT_TOMORROW_PRICE_SENSOR,
    DEFAULT_DISCHARGE_POWER_ENTITY,
    DEFAULT_BATTERY_CAPACITY,
    DEFAULT_CHARGE_POWER,
    DEFAULT_MAX_DISCHARGE_POWER,
    DEFAULT_BATTERY_EFFICIENCY,
    DEFAULT_MIN_SOC,
    DEFAULT_MAX_SOC,
    SERVICE_OPTIMIZE,
    STATUS_IDLE,
    STATUS_OPTIMIZING,
    STATUS_READY,
    STATUS_EXECUTING,
    STATUS_ERROR,
)
from .optimizer import BatteryOptimizer, BatteryAction, OptimizationResult

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.BUTTON]


def _parse_price_data(prices: list, source_format: str = "auto") -> list[dict]:
    """Parse price data from different sensor formats into a unified format.

    Returns a list of dicts with keys: hour, price, start (datetime)
    """
    parsed = []

    if not prices:
        return parsed

    for entry in prices:
        try:
            # Get the price value
            price = None
            if isinstance(entry.get("price"), (int, float)):
                price = float(entry["price"])
            elif isinstance(entry.get("value"), (int, float)):
                price = float(entry["value"])

            if price is None:
                continue

            # Get the start time
            start_str = entry.get("start") or entry.get("hour")
            if not start_str:
                continue

            # Parse datetime
            if isinstance(start_str, datetime):
                start_dt = start_str
            elif isinstance(start_str, str):
                # Try different formats
                for fmt in [
                    "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%dT%H:%M:%S.%f%z",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f",
                ]:
                    try:
                        start_dt = datetime.strptime(start_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    _LOGGER.warning("Could not parse datetime: %s", start_str)
                    continue
            else:
                continue

            # Make timezone-naive for comparison
            if start_dt.tzinfo is not None:
                start_dt = start_dt.replace(tzinfo=None)

            parsed.append({
                "start": start_dt,
                "price": price,
            })

        except Exception as e:
            _LOGGER.debug("Error parsing price entry %s: %s", entry, e)
            continue

    return parsed


def _get_int(value: Any, default: int) -> int:
    """Safely get an integer value."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _get_float(value: Any, default: float) -> float:
    """Safely get a float value."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SmartHomeEnergy from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = SmartChargeCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_start()

    # Register services
    async def handle_optimize(call: ServiceCall) -> None:
        """Handle optimize service call."""
        await coordinator.async_run_optimization()

    hass.services.async_register(
        DOMAIN,
        SERVICE_OPTIMIZE,
        handle_optimize,
        schema=vol.Schema({}),
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_stop()

    # Remove services if no more entries
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_OPTIMIZE)

    return unload_ok


class SmartChargeCoordinator:
    """Coordinator for smart battery charging/discharging with optimization."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self._unsub_timer = None
        self._unsub_hourly = None
        self._unsub_midnight = None

        # State
        self._enabled = True
        self._status = STATUS_IDLE
        self._current_action = BatteryAction.IDLE
        self._optimization_result: OptimizationResult | None = None
        self._last_optimization: datetime | None = None
        self._listeners: list[callable] = []
        self._is_force_charging = False

        # Initialize optimizer
        self._optimizer = BatteryOptimizer(
            battery_capacity_kwh=self.battery_capacity,
            max_charge_power_w=self.charge_power,
            max_discharge_power_w=self.max_discharge_power,
            battery_efficiency=self.battery_efficiency / 100.0,
            min_soc_percent=self.min_soc,
            max_soc_percent=self.max_soc,
        )

    # Configuration properties
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
    def battery_capacity(self) -> float:
        return _get_float(
            self.entry.options.get(CONF_BATTERY_CAPACITY,
                                   self.entry.data.get(CONF_BATTERY_CAPACITY)),
            DEFAULT_BATTERY_CAPACITY
        )

    @property
    def charge_power(self) -> int:
        return _get_int(
            self.entry.options.get(CONF_CHARGE_POWER,
                                   self.entry.data.get(CONF_CHARGE_POWER)),
            DEFAULT_CHARGE_POWER
        )

    @property
    def max_discharge_power(self) -> int:
        return _get_int(
            self.entry.options.get(CONF_MAX_DISCHARGE_POWER,
                                   self.entry.data.get(CONF_MAX_DISCHARGE_POWER)),
            DEFAULT_MAX_DISCHARGE_POWER
        )

    @property
    def battery_efficiency(self) -> int:
        return _get_int(
            self.entry.options.get(CONF_BATTERY_EFFICIENCY,
                                   self.entry.data.get(CONF_BATTERY_EFFICIENCY)),
            DEFAULT_BATTERY_EFFICIENCY
        )

    @property
    def min_soc(self) -> int:
        return _get_int(
            self.entry.options.get(CONF_MIN_SOC,
                                   self.entry.data.get(CONF_MIN_SOC)),
            DEFAULT_MIN_SOC
        )

    @property
    def max_soc(self) -> int:
        return _get_int(
            self.entry.options.get(CONF_MAX_SOC,
                                   self.entry.data.get(CONF_MAX_SOC)),
            DEFAULT_MAX_SOC
        )

    # State properties
    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        self._notify_listeners()

    @property
    def status(self) -> str:
        return self._status

    @property
    def current_action(self) -> BatteryAction:
        return self._current_action

    @property
    def optimization_result(self) -> OptimizationResult | None:
        return self._optimization_result

    @property
    def last_optimization(self) -> datetime | None:
        return self._last_optimization

    @property
    def hourly_plan(self) -> list[dict]:
        """Get hourly plan as list of dicts for sensor attributes."""
        if not self._optimization_result or not self._optimization_result.success:
            return []
        return [h.to_dict() for h in self._optimization_result.hourly_plan]

    @property
    def current_hour_plan(self) -> dict | None:
        """Get plan for current hour."""
        if not self._optimization_result or not self._optimization_result.success:
            return None

        current_hour = datetime.now().hour
        for plan in self._optimization_result.hourly_plan:
            if plan.hour == current_hour:
                return plan.to_dict()
        return None

    @property
    def next_action_plan(self) -> dict | None:
        """Get next non-idle action."""
        if not self._optimization_result or not self._optimization_result.success:
            return None

        current_hour = datetime.now().hour
        for plan in self._optimization_result.hourly_plan:
            if plan.hour > current_hour and plan.action != BatteryAction.IDLE:
                return plan.to_dict()
        return None

    # Listener management
    def add_listener(self, callback: callable) -> callable:
        self._listeners.append(callback)
        return lambda: self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        for listener in self._listeners:
            try:
                listener()
            except Exception as e:
                _LOGGER.error("Error notifying listener: %s", e)

    # Lifecycle
    async def async_start(self) -> None:
        """Start the coordinator."""
        _LOGGER.info("SmartHomeEnergy starting...")

        # Run initial optimization
        await self.async_run_optimization()

        # Update every minute to execute plan
        self._unsub_timer = async_track_time_interval(
            self.hass, self._async_execute_plan, timedelta(minutes=1)
        )

        # Re-optimize at the start of each hour
        self._unsub_hourly = async_track_time_change(
            self.hass, self._async_hourly_update, minute=1, second=0
        )

        # Full re-optimization at midnight
        self._unsub_midnight = async_track_time_change(
            self.hass, self._async_midnight_optimization, hour=0, minute=5, second=0
        )

        _LOGGER.info("SmartHomeEnergy started successfully")

    async def async_stop(self) -> None:
        """Stop the coordinator."""
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        if self._unsub_hourly:
            self._unsub_hourly()
            self._unsub_hourly = None
        if self._unsub_midnight:
            self._unsub_midnight()
            self._unsub_midnight = None

    # Optimization
    async def async_run_optimization(self) -> bool:
        """Run the optimization algorithm."""
        _LOGGER.info("Starting optimization...")
        self._status = STATUS_OPTIMIZING
        self._notify_listeners()

        try:
            # Get price data from main sensor
            state = self.hass.states.get(self.price_sensor)
            if state is None:
                _LOGGER.error("Price sensor %s not found", self.price_sensor)
                self._status = STATUS_ERROR
                self._notify_listeners()
                return False

            all_raw_prices = []

            # Try Strømligning format first (prices attribute)
            prices_attr = state.attributes.get("prices")
            if prices_attr:
                _LOGGER.debug("Using Strømligning format (prices attribute)")
                all_raw_prices.extend(prices_attr)

                # Get tomorrow's prices from binary sensor
                tomorrow_sensor = self.price_sensor.replace(
                    "sensor.", "binary_sensor."
                ).replace("current_price", "tomorrow_spotprice")

                tomorrow_state = self.hass.states.get(tomorrow_sensor)
                if tomorrow_state:
                    tomorrow_prices = tomorrow_state.attributes.get("prices") or []
                    if tomorrow_prices:
                        _LOGGER.debug("Got %d tomorrow prices from %s", len(tomorrow_prices), tomorrow_sensor)
                        all_raw_prices.extend(tomorrow_prices)
                else:
                    _LOGGER.debug("Tomorrow sensor %s not found", tomorrow_sensor)

            else:
                # Try Energi Data Service format (raw_today/raw_tomorrow)
                raw_today = state.attributes.get("raw_today") or []
                raw_tomorrow = state.attributes.get("raw_tomorrow") or []
                all_raw_prices = raw_today + raw_tomorrow
                _LOGGER.debug("Using Energi Data Service format")

            if not all_raw_prices:
                _LOGGER.error("No price data available from sensor %s", self.price_sensor)
                self._status = STATUS_ERROR
                self._notify_listeners()
                return False

            # Parse prices into unified format
            all_prices = _parse_price_data(all_raw_prices)

            if not all_prices:
                _LOGGER.error("Could not parse any price data")
                self._status = STATUS_ERROR
                self._notify_listeners()
                return False

            _LOGGER.debug("Got %d parsed price entries", len(all_prices))

            # Run optimization
            result = self._optimizer.optimize(
                prices=all_prices,
                current_soc_kwh=0.0,  # TODO: Get actual SOC from battery sensor
            )

            if result.success:
                self._optimization_result = result
                self._last_optimization = datetime.now()
                self._status = STATUS_READY

                # Log the plan
                charge_hours = [p.hour for p in result.hourly_plan if p.action == BatteryAction.CHARGE]
                discharge_hours = [p.hour for p in result.hourly_plan if p.action == BatteryAction.DISCHARGE]
                _LOGGER.info(
                    "Optimization complete: charge_hours=%s, discharge_hours=%s, net_benefit=%.2f DKK",
                    charge_hours, discharge_hours, result.net_benefit
                )
            else:
                _LOGGER.error("Optimization failed: %s", result.error_message)
                self._status = STATUS_ERROR

            self._notify_listeners()
            return result.success

        except Exception as e:
            _LOGGER.error("Optimization error: %s", e)
            self._status = STATUS_ERROR
            self._notify_listeners()
            return False

    async def _async_hourly_update(self, now: datetime) -> None:
        """Called at the start of each hour."""
        _LOGGER.debug("Hourly update at %s", now)
        # Re-run optimization if we're past noon and have tomorrow's prices
        if now.hour >= 13:
            await self.async_run_optimization()

    async def _async_midnight_optimization(self, now: datetime) -> None:
        """Called at midnight for daily optimization."""
        _LOGGER.info("Midnight optimization triggered")
        await self.async_run_optimization()

    # Plan execution
    async def _async_execute_plan(self, now: datetime | None = None) -> None:
        """Execute the current plan."""
        if not self._enabled:
            _LOGGER.debug("Execution skipped - not enabled")
            return

        if not self._optimization_result or not self._optimization_result.success:
            _LOGGER.debug("Execution skipped - no valid plan")
            return

        self._status = STATUS_EXECUTING
        current_hour = datetime.now().hour

        # Find action for current hour
        action, plan = self._optimizer.get_action_for_hour(
            self._optimization_result, current_hour
        )

        _LOGGER.debug(
            "Executing plan: hour=%d, action=%s, current_action=%s",
            current_hour, action.value, self._current_action.value
        )

        try:
            if action == BatteryAction.CHARGE:
                if self._current_action != BatteryAction.CHARGE:
                    _LOGGER.info("Starting charge at hour %d", current_hour)
                    await self._start_force_charge()
                    # Also set discharge to 0 during charging
                    await self._set_discharge_power(0)
                self._current_action = BatteryAction.CHARGE

            elif action == BatteryAction.DISCHARGE:
                if self._current_action != BatteryAction.DISCHARGE:
                    _LOGGER.info("Starting discharge at hour %d", current_hour)
                    await self._stop_force_charge()
                    await self._set_discharge_power(self.max_discharge_power)
                self._current_action = BatteryAction.DISCHARGE

            else:  # IDLE
                if self._current_action != BatteryAction.IDLE:
                    _LOGGER.info("Going idle at hour %d", current_hour)
                    await self._stop_force_charge()
                    await self._set_discharge_power(0)
                self._current_action = BatteryAction.IDLE

            self._notify_listeners()

        except Exception as e:
            _LOGGER.error("Error executing plan: %s", e)

    # Battery control
    async def _start_force_charge(self) -> None:
        """Start force charging the battery."""
        if not self.battery_device_id:
            _LOGGER.warning("No battery device ID configured")
            return

        try:
            _LOGGER.info("Calling huawei_solar.forcible_charge with power=%d", self.charge_power)
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
            _LOGGER.info("Force charge started successfully")
        except Exception as e:
            _LOGGER.error("Failed to start force charge: %s", e)

    async def _stop_force_charge(self) -> None:
        """Stop force charging."""
        if self._is_force_charging and self.battery_device_id:
            try:
                _LOGGER.info("Stopping force charge")
                await self.hass.services.async_call(
                    "huawei_solar",
                    "stop_forcible_charge",
                    {"device_id": self.battery_device_id}
                )
                self._is_force_charging = False
                _LOGGER.info("Force charge stopped successfully")
            except Exception as e:
                _LOGGER.error("Failed to stop force charge: %s", e)

    async def _set_discharge_power(self, power: int) -> None:
        """Set maximum discharge power."""
        _LOGGER.info("Setting discharge power to %d on %s", power, self.discharge_power_entity)
        try:
            await self.hass.services.async_call(
                "number",
                "set_value",
                {
                    "entity_id": self.discharge_power_entity,
                    "value": power,
                }
            )
            _LOGGER.info("Discharge power set to %d successfully", power)
        except Exception as e:
            _LOGGER.error("Failed to set discharge power: %s", e)
