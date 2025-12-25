"""Constants for SmartHomeEnergy."""

DOMAIN = "smarthomeenergy"

CONF_PRICE_SENSOR = "price_sensor"
CONF_BATTERY_DEVICE_ID = "battery_device_id"
CONF_DISCHARGE_POWER_ENTITY = "discharge_power_entity"
CONF_CHEAPEST_CHARGE_HOURS = "cheapest_charge_hours"
CONF_EXPENSIVE_DISCHARGE_HOURS = "expensive_discharge_hours"
CONF_NIGHT_START = "night_start"
CONF_NIGHT_END = "night_end"
CONF_CHARGE_POWER = "charge_power"
CONF_MAX_DISCHARGE_POWER = "max_discharge_power"

DEFAULT_PRICE_SENSOR = "sensor.energi_data_service"
DEFAULT_DISCHARGE_POWER_ENTITY = "number.battery_maximum_discharging_power"
DEFAULT_CHEAPEST_CHARGE_HOURS = 2
DEFAULT_EXPENSIVE_DISCHARGE_HOURS = 5
DEFAULT_NIGHT_START = 0
DEFAULT_NIGHT_END = 6
DEFAULT_CHARGE_POWER = 2500
DEFAULT_MAX_DISCHARGE_POWER = 2500
