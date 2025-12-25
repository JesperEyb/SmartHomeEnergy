"""Switch for SmartHomeEnergy."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SmartHomeEnergy switch."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SmartHomeEnergySwitch(coordinator, entry)])


class SmartHomeEnergySwitch(SwitchEntity):
    """Switch to enable/disable SmartHomeEnergy."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        self._coordinator = coordinator
        self._entry = entry
        self._attr_name = "SmartHomeEnergy Aktiv"
        self._attr_unique_id = f"{entry.entry_id}_enabled"
        self._attr_icon = "mdi:battery-heart"
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

    @property
    def is_on(self) -> bool:
        """Return true if enabled."""
        return self._coordinator.enabled

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on (enable) SmartHomeEnergy."""
        self._coordinator.enabled = True

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off (disable) SmartHomeEnergy."""
        self._coordinator.enabled = False
