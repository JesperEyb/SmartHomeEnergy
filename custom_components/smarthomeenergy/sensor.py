"""Sensors for SmartHomeEnergy."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATUS_READY, STATUS_EXECUTING
from .optimizer import BatteryAction


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SmartHomeEnergy sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        SmartHomeEnergyStatusSensor(coordinator, entry),
        SmartHomeEnergyActionSensor(coordinator, entry),
        SmartHomeEnergyPlanSensor(coordinator, entry),
        SmartHomeEnergyNextActionSensor(coordinator, entry),
        SmartHomeEnergyBenefitSensor(coordinator, entry),
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


class SmartHomeEnergyStatusSensor(SmartHomeEnergyBaseSensor):
    """Sensor showing optimization status."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Status", "status")
        self._attr_icon = "mdi:state-machine"

    @property
    def native_value(self) -> str:
        """Return current status."""
        status = self._coordinator.status
        status_map = {
            "idle": "Venter",
            "optimizing": "Optimerer...",
            "ready": "Plan klar",
            "executing": "Udfører plan",
            "error": "Fejl",
        }
        return status_map.get(status, status)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        attrs = {
            "status_raw": self._coordinator.status,
            "enabled": self._coordinator.enabled,
            "current_hour": datetime.now().hour,
        }

        if self._coordinator.last_optimization:
            attrs["last_optimization"] = self._coordinator.last_optimization.isoformat()

        result = self._coordinator.optimization_result
        if result:
            attrs.update(result.to_dict())

        return attrs


class SmartHomeEnergyActionSensor(SmartHomeEnergyBaseSensor):
    """Sensor showing current battery action."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Handling", "action")

    @property
    def native_value(self) -> str:
        """Return current action."""
        action = self._coordinator.current_action
        action_map = {
            BatteryAction.IDLE: "Idle",
            BatteryAction.CHARGE: "Oplader",
            BatteryAction.DISCHARGE: "Aflader",
        }
        return action_map.get(action, str(action))

    @property
    def icon(self) -> str:
        """Return icon based on action."""
        action = self._coordinator.current_action
        if action == BatteryAction.CHARGE:
            return "mdi:battery-charging"
        elif action == BatteryAction.DISCHARGE:
            return "mdi:battery-minus"
        return "mdi:battery"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        attrs = {
            "action_raw": self._coordinator.current_action.value,
            "current_hour": datetime.now().hour,
        }

        current_plan = self._coordinator.current_hour_plan
        if current_plan:
            attrs["current_hour_plan"] = current_plan

        return attrs


class SmartHomeEnergyPlanSensor(SmartHomeEnergyBaseSensor):
    """Sensor showing the daily plan."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Dagsplan", "plan")
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> str:
        """Return plan summary."""
        plan = self._coordinator.hourly_plan
        if not plan:
            return "Ingen plan"

        charge_hours = sum(1 for p in plan if p.get("action") == "charge")
        discharge_hours = sum(1 for p in plan if p.get("action") == "discharge")

        return f"{charge_hours} opladning, {discharge_hours} afladning"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the hourly plan summary."""
        plan = self._coordinator.hourly_plan
        current_hour = datetime.now().hour

        # Calculate charge and discharge hours
        charge_hours = [p["hour"] for p in plan if p.get("action") == "charge"]
        discharge_hours = [p["hour"] for p in plan if p.get("action") == "discharge"]

        # Create compact hourly summary (only hour and action)
        hourly_summary = [
            {"h": p.get("hour"), "a": p.get("action", "idle")[0]}  # i=idle, c=charge, d=discharge
            for p in plan
        ]

        attrs = {
            "charge_hours": charge_hours,
            "discharge_hours": discharge_hours,
            "current_hour": current_hour,
            "hours_planned": len(plan),
            "hourly_summary": hourly_summary,
            "hourly_plan": plan,  # Full plan with all details for graphing
        }

        result = self._coordinator.optimization_result
        if result:
            attrs["optimization_time"] = result.optimization_time.isoformat()
            attrs["net_benefit"] = round(result.net_benefit, 2)

        return attrs


class SmartHomeEnergyNextActionSensor(SmartHomeEnergyBaseSensor):
    """Sensor showing next scheduled action."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Naeste Handling", "next_action")
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> str:
        """Return next action."""
        next_plan = self._coordinator.next_action_plan
        if not next_plan:
            return "Ingen planlagt"

        action = next_plan.get("action", "idle")
        hour = next_plan.get("hour", 0)

        action_text = {
            "charge": "Opladning",
            "discharge": "Afladning",
        }.get(action, action)

        return f"{action_text} kl. {hour:02d}:00"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        attrs = {
            "current_hour": datetime.now().hour,
        }

        next_plan = self._coordinator.next_action_plan
        if next_plan:
            attrs["next_action_details"] = next_plan

        return attrs


class SmartHomeEnergyBenefitSensor(SmartHomeEnergyBaseSensor):
    """Sensor showing expected economic benefit."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Forventet Gevinst", "benefit")
        self._attr_icon = "mdi:currency-usd"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "DKK"

    @property
    def native_value(self) -> float | None:
        """Return expected net benefit."""
        result = self._coordinator.optimization_result
        if not result or not result.success:
            return None

        return round(result.net_benefit, 2)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        result = self._coordinator.optimization_result
        if not result or not result.success:
            return {}

        return {
            "total_charge_cost": round(result.total_charge_cost, 2),
            "total_discharge_revenue": round(result.total_discharge_revenue, 2),
            "net_benefit": round(result.net_benefit, 2),
            "estimated_cycles": round(result.total_cycles, 3),
        }
