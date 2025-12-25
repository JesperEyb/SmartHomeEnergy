# SmartHomeEnergy

Smart battery optimization for Home Assistant with Huawei Solar.

## Features

- **Automatic Price Optimization**: Uses a greedy algorithm to find optimal charge/discharge times based on electricity prices
- **Daily Planning**: Creates a 24-hour plan showing when to charge, discharge, or stay idle
- **Visual Dashboard**: Sensors showing current status, plan, next action, and expected savings
- **Manual Control**: Button to trigger optimization on demand
- **Automatic Updates**: Re-optimizes at midnight and when new prices are available

## How it Works

1. Fetches electricity prices from Energi Data Service
2. Analyzes prices to find cheapest hours for charging and most expensive for discharging
3. Creates an optimized schedule considering battery capacity and efficiency
4. Automatically executes the plan using Huawei Solar's force charge and discharge control

## Entities

| Entity | Description |
|--------|-------------|
| `sensor.smarthomeenergy_status` | Current status (optimizing, ready, executing, error) |
| `sensor.smarthomeenergy_handling` | Current action (idle, charging, discharging) |
| `sensor.smarthomeenergy_dagsplan` | Daily plan with hourly breakdown |
| `sensor.smarthomeenergy_naeste_handling` | Next scheduled action |
| `sensor.smarthomeenergy_forventet_gevinst` | Expected economic benefit |
| `switch.smarthomeenergy_aktiv` | Enable/disable automatic control |
| `button.smarthomeenergy_optimer` | Manually trigger optimization |

## Installation

### HACS
1. Add this repository as a custom repository in HACS
2. Install SmartHomeEnergy
3. Restart Home Assistant
4. Add integration via Settings -> Devices & Services

### Manual
Copy `custom_components/smarthomeenergy` to your Home Assistant config folder.

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| Price sensor | Electricity price sensor (e.g., sensor.energi_data_service) | - |
| Battery device | Your Huawei Solar battery device | - |
| Discharge power entity | number.battery_maximum_discharging_power | - |
| Battery capacity | Total capacity in kWh | 10 |
| Charge power | Maximum charge power in W | 2500 |
| Max discharge power | Maximum discharge power in W | 2500 |
| Battery efficiency | Round-trip efficiency in % | 90 |
| Min SOC | Minimum state of charge in % | 10 |
| Max SOC | Maximum state of charge in % | 100 |

## Service

### smarthomeenergy.optimize
Triggers the optimization algorithm to create a new plan.

```yaml
service: smarthomeenergy.optimize
```

## Requirements

- Home Assistant 2024.1+
- Huawei Solar integration
- Energi Data Service integration (or similar price sensor with raw_today/raw_tomorrow attributes)

## License

MIT
