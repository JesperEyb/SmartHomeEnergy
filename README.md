# SmartHomeEnergy

Smart battery charging integration for Home Assistant with Huawei Solar.

## Features
- Automatically charge battery during cheapest hours at night
- Only allow discharge during most expensive hours during the day
- Works with Energi Data Service for electricity prices

## Installation

### HACS
1. Add this repository as a custom repository in HACS
2. Install SmartHomeEnergy
3. Restart Home Assistant
4. Add integration via Settings -> Devices & Services

### Manual
Copy `custom_components/smarthomeenergy` to your Home Assistant config folder.

## Configuration
- Price sensor: Your electricity price sensor (e.g., sensor.energi_data_service)
- Battery device: Your Huawei Solar battery
- Discharge power entity: number.battery_maximum_discharging_power
- Cheapest charge hours: Number of hours to charge (default: 2)
- Expensive discharge hours: Number of hours to allow discharge (default: 5)
