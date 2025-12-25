"""Button for SmartHomeEnergy."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SmartHomeEnergy button."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SmartHomeEnergyScanButton(coordinator, entry)])


class SmartHomeEnergyScanButton(ButtonEntity):
    """Button to trigger price scan and plan recalculation."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        self._coordinator = coordinator
        self._entry = entry
        self._attr_name = "SmartHomeEnergy Scan Priser"
        self._attr_unique_id = f"{entry.entry_id}_scan"
        self._attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        """Handle button press."""
        await self._coordinator.async_scan_and_plan()
