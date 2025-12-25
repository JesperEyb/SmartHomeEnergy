"""Greedy battery optimizer for SmartHomeEnergy."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

_LOGGER = logging.getLogger(__name__)


class BatteryAction(Enum):
    """Battery action types."""
    IDLE = "idle"
    CHARGE = "charge"
    DISCHARGE = "discharge"


@dataclass
class HourlyPlan:
    """Plan for a single hour."""
    hour: int
    datetime_start: datetime
    action: BatteryAction
    buy_price: float
    sell_price: float
    charge_kwh: float = 0.0
    discharge_kwh: float = 0.0
    expected_cost: float = 0.0
    expected_revenue: float = 0.0
    soc_start: float = 0.0
    soc_end: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for sensor attributes."""
        return {
            "hour": self.hour,
            "time": f"{self.hour:02d}:00",
            "datetime": self.datetime_start.isoformat(),
            "action": self.action.value,
            "buy_price": round(self.buy_price, 4),
            "sell_price": round(self.sell_price, 4),
            "charge_kwh": round(self.charge_kwh, 3),
            "discharge_kwh": round(self.discharge_kwh, 3),
            "expected_cost": round(self.expected_cost, 2),
            "expected_revenue": round(self.expected_revenue, 2),
            "soc_start": round(self.soc_start, 2),
            "soc_end": round(self.soc_end, 2),
        }


@dataclass
class OptimizationResult:
    """Result of battery optimization."""
    success: bool
    hourly_plan: list[HourlyPlan] = field(default_factory=list)
    total_charge_cost: float = 0.0
    total_discharge_revenue: float = 0.0
    net_benefit: float = 0.0
    total_cycles: float = 0.0
    optimization_time: datetime = field(default_factory=datetime.now)
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for sensor attributes."""
        return {
            "success": self.success,
            "total_charge_cost": round(self.total_charge_cost, 2),
            "total_discharge_revenue": round(self.total_discharge_revenue, 2),
            "net_benefit": round(self.net_benefit, 2),
            "total_cycles": round(self.total_cycles, 3),
            "optimization_time": self.optimization_time.isoformat(),
            "error_message": self.error_message,
            "hours_planned": len(self.hourly_plan),
        }


class BatteryOptimizer:
    """Greedy battery optimizer based on electricity prices."""

    def __init__(
        self,
        battery_capacity_kwh: float,
        max_charge_power_w: float,
        max_discharge_power_w: float,
        battery_efficiency: float = 0.90,
        min_soc_percent: float = 10.0,
        max_soc_percent: float = 100.0,
    ) -> None:
        """Initialize the optimizer.

        Args:
            battery_capacity_kwh: Battery capacity in kWh
            max_charge_power_w: Maximum charge power in Watts
            max_discharge_power_w: Maximum discharge power in Watts
            battery_efficiency: Round-trip efficiency (0-1)
            min_soc_percent: Minimum state of charge (%)
            max_soc_percent: Maximum state of charge (%)
        """
        self.battery_capacity_kwh = battery_capacity_kwh
        self.max_charge_power_kw = max_charge_power_w / 1000.0
        self.max_discharge_power_kw = max_discharge_power_w / 1000.0
        self.efficiency = battery_efficiency
        self.sqrt_efficiency = battery_efficiency ** 0.5
        self.min_soc_kwh = battery_capacity_kwh * min_soc_percent / 100.0
        self.max_soc_kwh = battery_capacity_kwh * max_soc_percent / 100.0

    def optimize(
        self,
        prices: list[dict],
        current_soc_kwh: float = 0.0,
        start_hour: int | None = None,
    ) -> OptimizationResult:
        """Run greedy optimization on price data.

        Args:
            prices: List of price dicts with 'hour' (datetime) and 'price' (float)
            current_soc_kwh: Current battery state of charge in kWh
            start_hour: Hour to start optimization from (None = current hour)

        Returns:
            OptimizationResult with hourly plan
        """
        try:
            if not prices:
                return OptimizationResult(
                    success=False,
                    error_message="No price data available"
                )

            # Parse and sort prices by datetime
            parsed_prices = self._parse_prices(prices)
            if not parsed_prices:
                return OptimizationResult(
                    success=False,
                    error_message="Could not parse price data"
                )

            # Filter to next 24 hours from start
            now = datetime.now()
            if start_hour is not None:
                start_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            else:
                start_time = now.replace(minute=0, second=0, microsecond=0)

            end_time = start_time + timedelta(hours=24)

            # Filter prices to planning window
            planning_prices = [
                p for p in parsed_prices
                if start_time <= p["datetime"] < end_time
            ]

            if not planning_prices:
                return OptimizationResult(
                    success=False,
                    error_message="No prices in planning window"
                )

            # Sort by datetime
            planning_prices.sort(key=lambda x: x["datetime"])

            # Calculate buy/sell prices (sell price typically lower due to fees)
            # Assuming sell price is 70% of buy price (adjust as needed)
            for p in planning_prices:
                p["buy_price"] = p["price"]
                p["sell_price"] = max(0, p["price"] * 0.7)  # Simplified sell price

            # Run greedy optimization
            hourly_plan = self._greedy_optimize(planning_prices, current_soc_kwh)

            # Calculate totals
            total_charge_cost = sum(h.expected_cost for h in hourly_plan)
            total_discharge_revenue = sum(h.expected_revenue for h in hourly_plan)
            total_charged = sum(h.charge_kwh for h in hourly_plan)
            total_cycles = total_charged / self.battery_capacity_kwh if self.battery_capacity_kwh > 0 else 0

            return OptimizationResult(
                success=True,
                hourly_plan=hourly_plan,
                total_charge_cost=total_charge_cost,
                total_discharge_revenue=total_discharge_revenue,
                net_benefit=total_discharge_revenue - total_charge_cost,
                total_cycles=total_cycles,
                optimization_time=datetime.now(),
            )

        except Exception as e:
            _LOGGER.error("Optimization failed: %s", e)
            return OptimizationResult(
                success=False,
                error_message=str(e)
            )

    def _parse_prices(self, prices: list[dict]) -> list[dict]:
        """Parse price data into consistent format."""
        parsed = []
        for p in prices:
            try:
                hour_dt = p.get("hour") or p.get("start")
                price = p.get("price") or p.get("value")

                if hour_dt is None or price is None:
                    continue

                if isinstance(hour_dt, str):
                    hour_dt = datetime.fromisoformat(hour_dt.replace("Z", "+00:00"))

                # Make timezone naive for comparison
                if hasattr(hour_dt, 'tzinfo') and hour_dt.tzinfo is not None:
                    hour_dt = hour_dt.replace(tzinfo=None)

                parsed.append({
                    "datetime": hour_dt,
                    "hour": hour_dt.hour,
                    "price": float(price),
                })
            except (ValueError, TypeError) as e:
                _LOGGER.debug("Failed to parse price entry: %s", e)
                continue

        return parsed

    def _greedy_optimize(
        self,
        prices: list[dict],
        current_soc: float,
    ) -> list[HourlyPlan]:
        """Greedy optimization algorithm.

        Strategy:
        1. Find hours with lowest prices for charging
        2. Find hours with highest prices for discharging
        3. Ensure charging happens before discharging
        4. Calculate expected costs and revenues
        """
        n_hours = len(prices)

        # Create indexed prices with original position
        indexed_prices = [(i, p["buy_price"]) for i, p in enumerate(prices)]

        # Sort by price to find cheapest and most expensive hours
        sorted_by_price = sorted(indexed_prices, key=lambda x: x[1])

        # Calculate how many hours we need to charge to fill battery
        available_capacity = self.max_soc_kwh - current_soc
        charge_per_hour = self.max_charge_power_kw * self.sqrt_efficiency
        hours_to_full = int((available_capacity / charge_per_hour) + 1) if charge_per_hour > 0 else 0

        # Calculate how many hours we can discharge
        discharge_per_hour = self.max_discharge_power_kw * self.sqrt_efficiency
        hours_to_empty = int((self.max_soc_kwh / discharge_per_hour) + 1) if discharge_per_hour > 0 else 0

        # Determine charge and discharge hours
        # Take cheapest hours for charging (up to what we need)
        n_charge_hours = min(hours_to_full, n_hours // 3)  # Max 1/3 of day for charging
        cheapest_indices = set(i for i, _ in sorted_by_price[:n_charge_hours])

        # Take most expensive hours for discharging (up to what we can)
        n_discharge_hours = min(hours_to_empty, n_hours // 3)  # Max 1/3 of day for discharging
        expensive_indices = set(i for i, _ in sorted_by_price[-n_discharge_hours:])

        # Remove overlap (prefer discharging over charging if same hour is both)
        cheapest_indices -= expensive_indices

        # Find minimum price for charging (for profit calculation)
        if cheapest_indices:
            min_charge_price = min(prices[i]["buy_price"] for i in cheapest_indices)
        else:
            min_charge_price = 0

        # Only discharge if sell price > charge price * efficiency
        profitable_discharge = set()
        for i in expensive_indices:
            sell_price = prices[i]["sell_price"]
            if sell_price > min_charge_price / self.efficiency:
                profitable_discharge.add(i)

        # Build the hourly plan
        hourly_plan = []
        soc = current_soc

        for i, p in enumerate(prices):
            hour_plan = HourlyPlan(
                hour=p["hour"],
                datetime_start=p["datetime"],
                action=BatteryAction.IDLE,
                buy_price=p["buy_price"],
                sell_price=p["sell_price"],
                soc_start=soc,
            )

            if i in cheapest_indices and soc < self.max_soc_kwh:
                # Charge
                charge_kwh = min(
                    self.max_charge_power_kw,
                    (self.max_soc_kwh - soc) / self.sqrt_efficiency
                )
                actual_stored = charge_kwh * self.sqrt_efficiency

                hour_plan.action = BatteryAction.CHARGE
                hour_plan.charge_kwh = charge_kwh
                hour_plan.expected_cost = charge_kwh * p["buy_price"]
                soc += actual_stored

            elif i in profitable_discharge and soc > self.min_soc_kwh:
                # Discharge
                discharge_kwh = min(
                    self.max_discharge_power_kw,
                    (soc - self.min_soc_kwh)
                )
                actual_delivered = discharge_kwh * self.sqrt_efficiency

                hour_plan.action = BatteryAction.DISCHARGE
                hour_plan.discharge_kwh = discharge_kwh
                hour_plan.expected_revenue = actual_delivered * p["sell_price"]
                soc -= discharge_kwh

            hour_plan.soc_end = soc
            hourly_plan.append(hour_plan)

        return hourly_plan

    def get_action_for_hour(
        self,
        result: OptimizationResult,
        hour: int,
    ) -> tuple[BatteryAction, HourlyPlan | None]:
        """Get the action for a specific hour.

        Args:
            result: Optimization result
            hour: Hour of day (0-23)

        Returns:
            Tuple of (action, plan) or (IDLE, None) if not found
        """
        if not result.success or not result.hourly_plan:
            return BatteryAction.IDLE, None

        for plan in result.hourly_plan:
            if plan.hour == hour:
                return plan.action, plan

        return BatteryAction.IDLE, None
