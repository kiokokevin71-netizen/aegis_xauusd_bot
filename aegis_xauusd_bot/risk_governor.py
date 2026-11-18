from dataclasses import dataclass
from typing import Tuple, List, Dict

@dataclass
class RiskVerdict:
    approved: bool
    lot_size: float
    risk_amount_usd: float
    reason: str

class DeterministicRiskGovernor:
    def __init__(self, initial_balance: float = 8000.0, risk_per_trade_pct: float = 0.50, max_daily_dd_pct: float = 2.00):
        self.initial_balance = initial_balance
        self.session_start_balance = initial_balance
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_daily_dd_pct = max_daily_dd_pct
        self.kill_switch_engaged = False

    def engage_kill_switch(self):
        self.kill_switch_engaged = True

    def reset_kill_switch(self, current_balance: float):
        self.kill_switch_engaged = False
        self.session_start_balance = current_balance

    def check_daily_drawdown(self, current_equity: float) -> Tuple[bool, float]:
        dd_usd = max(0.0, self.session_start_balance - current_equity)
        dd_pct = (dd_usd / self.session_start_balance) * 100.0 if self.session_start_balance > 0 else 100.0
        if dd_pct >= self.max_daily_dd_pct:
            self.kill_switch_engaged = True
            return False, dd_pct
        return True, dd_pct

    def evaluate_trade(
        self,
        current_equity: float,
        stop_loss_points: float,
        point_value: float,
        open_positions: List[Dict],
        min_lot: float = 0.01,
        max_lot: float = 5.00,
        lot_step: float = 0.01
    ) -> RiskVerdict:
        if self.kill_switch_engaged:
            return RiskVerdict(False, 0.0, 0.0, "VETO: Kill switch or daily circuit breaker active.")

        within_dd, dd_pct = self.check_daily_drawdown(current_equity)
        if not within_dd:
            return RiskVerdict(False, 0.0, 0.0, f"VETO: Daily drawdown limit reached ({dd_pct:.2f}% >= {self.max_daily_dd_pct:.2f}%).")

        if len(open_positions) >= 3:
            return RiskVerdict(False, 0.0, 0.0, "VETO: Maximum concurrent XAUUSD hedging legs (3) reached.")

        if stop_loss_points <= 0 or point_value <= 0:
            return RiskVerdict(False, 0.0, 0.0, "VETO: Invalid stop-loss distance or contract point value.")

        risk_usd = current_equity * (self.risk_per_trade_pct / 100.0)
        raw_lots = risk_usd / (stop_loss_points * point_value)

        steps = int(raw_lots / lot_step)
        sized_lots = round(max(min_lot, min(max_lot, steps * lot_step)), 2)

        actual_risk = sized_lots * stop_loss_points * point_value
        if actual_risk > risk_usd * 1.15:
            return RiskVerdict(False, 0.0, actual_risk, f"VETO: Minimum lot size risk (${actual_risk:.2f}) exceeds budget (${risk_usd:.2f}).")

        return RiskVerdict(True, sized_lots, round(actual_risk, 2), f"XAUUSD APPROVED: {sized_lots} lots | Risk ${actual_risk:.2f} ({self.risk_per_trade_pct:.2f}%)")
