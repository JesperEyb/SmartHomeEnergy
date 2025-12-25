"""Sensors for SmartHomeEnergy."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SmartHomeEnergy sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        SmartHomeEnergyModeSensor(coordinator, entry),
        SmartHomeEnergyChargePlanSensor(coordinator, entry),
        SmartHomeEnergyDischargePlanSensor(coordinator, entry),
        SmartHomeEnergyNextActionSensor(coordinator, entry),
        SmartHomeEnergyHourlyPlanSensor(coordinator, entry),
    ])


class SmartHomeEnergyBaseSensor(SensorEntity):
    """Base sensor for SmartHomeEnergy."""

    def __init__(self, coordinator, entry: ConfigEntry, name: str, unique_suffix: str) -> None:
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._entry = entry
        self._attr_name = f"SmartHomeEnergy {name}"
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        """Run when entity is added."""
        self._unsub = self._coordinator.add_listener(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity is removed."""
        if self._unsub:
            self._unsub()

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator update."""
        self.async_write_ha_state()


class SmartHomeEnergyModeSensor(SmartHomeEnergyBaseSensor):
    """Sensor showing current mode."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Mode", "mode")
        self._attr_icon = "mdi:battery-sync"

    @property
    def native_value(self) -> str:
        """Return current mode."""
        mode = self._coordinator.current_mode
        mode_map = {
            "idle": "Idle",
            "charging": "Oplader",
            "discharge_allowed": "Afladning tilladt",
            "discharge_blocked": "Afladning blokeret",
        }
        return mode_map.get(mode, mode)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        return {
            "enabled": self._coordinator.enabled,
            "current_hour": datetime.now().hour,
        }


class SmartHomeEnergyChargePlanSensor(SmartHomeEnergyBaseSensor):
    """Sensor showing charge plan."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Opladningsplan", "charge_plan")
        self._attr_icon = "mdi:battery-charging"

    @property
    def native_value(self) -> str:
        """Return charge hours as string."""
        hours = sorted(self._coordinator.cheapest_charge_hours)
        if not hours:
            return "Ingen plan"
        return ", ".join(f"{int(h):02d}:00" for h in hours)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        hours = self._coordinator.cheapest_charge_hours
        current_hour = datetime.now().hour
        return {
            "charge_hours": hours,
            "is_charge_hour": current_hour in hours,
            "night_start": f"{int(self._coordinator.night_start):02d}:00",
            "night_end": f"{int(self._coordinator.night_end):02d}:00",
            "charge_power": self._coordinator.charge_power,
        }


class SmartHomeEnergyDischargePlanSensor(SmartHomeEnergyBaseSensor):
    """Sensor showing discharge plan."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Afladningsplan", "discharge_plan")
        self._attr_icon = "mdi:battery-minus"

    @property
    def native_value(self) -> str:
        """Return discharge hours as string."""
        hours = sorted(self._coordinator.expensive_discharge_hours)
        if not hours:
            return "Ingen plan"
        return ", ".join(f"{int(h):02d}:00" for h in hours)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        hours = self._coordinator.expensive_discharge_hours
        current_hour = datetime.now().hour

        # Get prices for display
        price_plan = []
        for p in self._coordinator.all_prices:
            hour = p["hour"].hour
            price_plan.append({
                "hour": f"{int(hour):02d}:00",
                "price": round(p["price"], 2),
                "is_charge": hour in self._coordinator.cheapest_charge_hours,
                "is_discharge": hour in self._coordinator.expensive_discharge_hours,
            })

        return {
            "discharge_hours": hours,
            "is_discharge_hour": current_hour in hours,
            "max_discharge_power": self._coordinator.max_discharge_power,
            "price_plan": price_plan[:24],  # Only today
        }


class SmartHomeEnergyNextActionSensor(SmartHomeEnergyBaseSensor):
    """Sensor showing next scheduled action."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Naeste Handling", "next_action")
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> str:
        """Return next action."""
        current_hour = datetime.now().hour
        charge_hours = sorted(self._coordinator.cheapest_charge_hours)
        discharge_hours = sorted(self._coordinator.expensive_discharge_hours)

        # Find next action
        for h in range(current_hour + 1, 24):
            if h in charge_hours:
                return f"Opladning kl. {int(h):02d}:00"
            if h in discharge_hours:
                return f"Afladning kl. {int(h):02d}:00"

        # Check tomorrow's charge hours
        for h in charge_hours:
            if h < current_hour:
                return f"Opladning kl. {int(h):02d}:00 (i morgen)"

        return "Ingen planlagt"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        return {
            "current_mode": self._coordinator.current_mode,
        }


class SmartHomeEnergyHourlyPlanSensor(SmartHomeEnergyBaseSensor):
    """Sensor showing hourly plan for the day."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Dagsplan", "hourly_plan")
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> str:
        """Return summary of the day plan."""
        plan = self._coordinator.hourly_plan
        if not plan:
            return "Ingen plan"

        charge_count = sum(1 for p in plan if p["action"] == "charge")
        discharge_count = sum(1 for p in plan if p["action"] == "discharge")
        return f"{charge_count} opladningstimer, {discharge_count} afladningstimer"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the full hourly plan."""
        plan = self._coordinator.hourly_plan
        current_hour = datetime.now().hour

        # Format plan for display
        formatted_plan = []
        for entry in plan:
            hour = entry["hour"]
            action = entry["action"]
            price = entry["price"]

            action_text = {
                "charge": "Opladning",
                "discharge": "Afladning",
                "blocked": "Blokeret",
                "night_idle": "Nat (idle)",
            }.get(action, action)

            formatted_plan.append({
                "time": f"{int(hour):02d}:00",
                "action": action_text,
                "action_raw": action,
                "price": round(price, 2) if price else None,
                "is_current": hour == current_hour,
            })

        return {
            "hourly_plan": formatted_plan,
            "current_hour": current_hour,
            "charge_hours": sorted(self._coordinator.cheapest_charge_hours),
            "discharge_hours": sorted(self._coordinator.expensive_discharge_hours),
        }
