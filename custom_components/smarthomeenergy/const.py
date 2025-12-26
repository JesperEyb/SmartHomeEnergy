"""Constants for SmartHomeEnergy."""

DOMAIN = "smarthomeenergy"

# Configuration keys
CONF_PRICE_SENSOR = "price_sensor"
CONF_SELL_PRICE_SENSOR = "sell_price_sensor"
CONF_BATTERY_SOC_SENSOR = "battery_soc_sensor"
CONF_BATTERY_DEVICE_ID = "battery_device_id"
CONF_DISCHARGE_POWER_ENTITY = "discharge_power_entity"
CONF_BATTERY_CAPACITY = "battery_capacity"
CONF_CHARGE_POWER = "charge_power"
CONF_MAX_DISCHARGE_POWER = "max_discharge_power"
CONF_BATTERY_EFFICIENCY = "battery_efficiency"
CONF_MIN_SOC = "min_soc"
CONF_MAX_SOC = "max_soc"
CONF_CHARGE_HOURS = "charge_hours"

# Legacy config keys (for backwards compatibility)
CONF_CHEAPEST_CHARGE_HOURS = "cheapest_charge_hours"
CONF_EXPENSIVE_DISCHARGE_HOURS = "expensive_discharge_hours"
CONF_NIGHT_START = "night_start"
CONF_NIGHT_END = "night_end"

# Default values
DEFAULT_PRICE_SENSOR = "sensor.stromligning_current_price_vat"
DEFAULT_SELL_PRICE_SENSOR = "sensor.stromligning_current_price_vat"  # Usually same as buy price for self-consumption
DEFAULT_BATTERY_SOC_SENSOR = "sensor.battery_state_of_capacity"
DEFAULT_TOMORROW_PRICE_SENSOR = "binary_sensor.stromligning_tomorrow_spotprice_vat"
DEFAULT_DISCHARGE_POWER_ENTITY = "number.battery_maximum_discharging_power"
DEFAULT_BATTERY_CAPACITY = 10.0  # kWh
DEFAULT_CHARGE_POWER = 2500  # W
DEFAULT_MAX_DISCHARGE_POWER = 2500  # W
DEFAULT_BATTERY_EFFICIENCY = 90  # %
DEFAULT_MIN_SOC = 10  # %
DEFAULT_MAX_SOC = 100  # %
DEFAULT_CHARGE_HOURS = 2  # hours

# Legacy defaults
DEFAULT_CHEAPEST_CHARGE_HOURS = 2
DEFAULT_EXPENSIVE_DISCHARGE_HOURS = 5
DEFAULT_NIGHT_START = 0
DEFAULT_NIGHT_END = 6

# Service names
SERVICE_OPTIMIZE = "optimize"
SERVICE_FORCE_CHARGE = "force_charge"
SERVICE_FORCE_DISCHARGE = "force_discharge"
SERVICE_STOP = "stop"

# Optimization status
STATUS_IDLE = "idle"
STATUS_OPTIMIZING = "optimizing"
STATUS_READY = "ready"
STATUS_EXECUTING = "executing"
STATUS_ERROR = "error"
