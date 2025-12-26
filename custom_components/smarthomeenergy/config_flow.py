"""Config flow for SmartHomeEnergy."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_PRICE_SENSOR,
    CONF_SELL_PRICE_SENSOR,
    CONF_BATTERY_SOC_SENSOR,
    CONF_BATTERY_DEVICE_ID,
    CONF_DISCHARGE_POWER_ENTITY,
    CONF_BATTERY_CAPACITY,
    CONF_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_BATTERY_EFFICIENCY,
    CONF_MIN_SOC,
    CONF_MAX_SOC,
    DEFAULT_PRICE_SENSOR,
    DEFAULT_SELL_PRICE_SENSOR,
    DEFAULT_BATTERY_SOC_SENSOR,
    DEFAULT_DISCHARGE_POWER_ENTITY,
    DEFAULT_BATTERY_CAPACITY,
    DEFAULT_CHARGE_POWER,
    DEFAULT_MAX_DISCHARGE_POWER,
    DEFAULT_BATTERY_EFFICIENCY,
    DEFAULT_MIN_SOC,
    DEFAULT_MAX_SOC,
)

_LOGGER = logging.getLogger(__name__)


class SmartHomeEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartHomeEnergy."""

    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title="SmartHomeEnergy",
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_PRICE_SENSOR, default=DEFAULT_PRICE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_SELL_PRICE_SENSOR, default=DEFAULT_SELL_PRICE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_BATTERY_SOC_SENSOR, default=DEFAULT_BATTERY_SOC_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_BATTERY_DEVICE_ID): selector.DeviceSelector(
                    selector.DeviceSelectorConfig(integration="huawei_solar")
                ),
                vol.Required(CONF_DISCHARGE_POWER_ENTITY, default=DEFAULT_DISCHARGE_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="number")
                ),
                vol.Required(CONF_BATTERY_CAPACITY, default=DEFAULT_BATTERY_CAPACITY): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=100, step=0.1, unit_of_measurement="kWh", mode="box")
                ),
                vol.Required(CONF_CHARGE_POWER, default=DEFAULT_CHARGE_POWER): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=500, max=10000, step=100, unit_of_measurement="W", mode="box")
                ),
                vol.Required(CONF_MAX_DISCHARGE_POWER, default=DEFAULT_MAX_DISCHARGE_POWER): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=500, max=10000, step=100, unit_of_measurement="W", mode="box")
                ),
                vol.Required(CONF_BATTERY_EFFICIENCY, default=DEFAULT_BATTERY_EFFICIENCY): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=70, max=100, step=1, unit_of_measurement="%", mode="slider")
                ),
                vol.Required(CONF_MIN_SOC, default=DEFAULT_MIN_SOC): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=50, step=5, unit_of_measurement="%", mode="slider")
                ),
                vol.Required(CONF_MAX_SOC, default=DEFAULT_MAX_SOC): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=50, max=100, step=5, unit_of_measurement="%", mode="slider")
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return SmartHomeEnergyOptionsFlow(config_entry)


class SmartHomeEnergyOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for SmartHomeEnergy."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Merge data and options for current values
        current = {**self._entry.data, **self._entry.options}

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PRICE_SENSOR,
                    default=current.get(CONF_PRICE_SENSOR, DEFAULT_PRICE_SENSOR)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(
                    CONF_SELL_PRICE_SENSOR,
                    default=current.get(CONF_SELL_PRICE_SENSOR, DEFAULT_SELL_PRICE_SENSOR)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(
                    CONF_BATTERY_SOC_SENSOR,
                    default=current.get(CONF_BATTERY_SOC_SENSOR, DEFAULT_BATTERY_SOC_SENSOR)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(
                    CONF_DISCHARGE_POWER_ENTITY,
                    default=current.get(CONF_DISCHARGE_POWER_ENTITY, DEFAULT_DISCHARGE_POWER_ENTITY)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="number")
                ),
                vol.Required(
                    CONF_BATTERY_CAPACITY,
                    default=current.get(CONF_BATTERY_CAPACITY, DEFAULT_BATTERY_CAPACITY)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=100, step=0.1, unit_of_measurement="kWh", mode="box")
                ),
                vol.Required(
                    CONF_CHARGE_POWER,
                    default=current.get(CONF_CHARGE_POWER, DEFAULT_CHARGE_POWER)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=500, max=10000, step=100, unit_of_measurement="W", mode="box")
                ),
                vol.Required(
                    CONF_MAX_DISCHARGE_POWER,
                    default=current.get(CONF_MAX_DISCHARGE_POWER, DEFAULT_MAX_DISCHARGE_POWER)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=500, max=10000, step=100, unit_of_measurement="W", mode="box")
                ),
                vol.Required(
                    CONF_BATTERY_EFFICIENCY,
                    default=current.get(CONF_BATTERY_EFFICIENCY, DEFAULT_BATTERY_EFFICIENCY)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=70, max=100, step=1, unit_of_measurement="%", mode="slider")
                ),
                vol.Required(
                    CONF_MIN_SOC,
                    default=current.get(CONF_MIN_SOC, DEFAULT_MIN_SOC)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=50, step=5, unit_of_measurement="%", mode="slider")
                ),
                vol.Required(
                    CONF_MAX_SOC,
                    default=current.get(CONF_MAX_SOC, DEFAULT_MAX_SOC)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=50, max=100, step=5, unit_of_measurement="%", mode="slider")
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
