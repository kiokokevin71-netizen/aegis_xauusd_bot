import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional

@dataclass
class RegimeState:
    regime: str
    atr_percentile: float
    spread_points: float
    tradable: bool
    note: str

@dataclass
class TradeProposal:
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    stop_loss_points: float
    strategy: str
    confidence: float

class RegimeContextAgent:
    def evaluate(self, df: pd.DataFrame, current_spread: float, max_spread: float = 35.0) -> RegimeState:
        if current_spread > max_spread:
            return RegimeState("HIGH_SPREAD_LOCKOUT", 0.0, current_spread, False, f"XAUUSD Spread {current_spread:.1f} exceeds limit {max_spread}")

        if len(df) < 30:
            return RegimeState("WARMING_UP", 50.0, current_spread, False, "Insufficient bars for XAUUSD analysis")

        high_low = df["high"] - df["low"]
        atr = high_low.rolling(14).mean()
        current_atr = atr.iloc[-1]
        pct = float((atr < current_atr).mean() * 100.0)

        if pct > 80.0:
            return RegimeState("GOLD_BREAKOUT", pct, current_spread, True, "High XAUUSD volatility expansion active")
        elif pct < 20.0:
            return RegimeState("GOLD_COMPRESSION", pct, current_spread, True, "Low XAUUSD volatility compression active")
        else:
            return RegimeState("GOLD_TRENDING", pct, current_spread, True, "Stable XAUUSD trend regime active")

class QuantSignalAgent:
    def generate_signal(self, symbol: str, df: pd.DataFrame, regime: RegimeState) -> Optional[TradeProposal]:
        if not regime.tradable or len(df) < 30:
            return None

        close = df["close"]
        ema_fast = close.ewm(span=9, adjust=False).mean()
        ema_slow = close.ewm(span=21, adjust=False).mean()
        atr = (df["high"] - df["low"]).rolling(14).mean().iloc[-1]

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = (100 - (100 / (1 + rs))).fillna(50.0).iloc[-1]

        price = float(close.iloc[-1])
        sl_dist = max(atr * 1.8, price * 0.002)
        tp_dist = sl_dist * 2.5

        if ema_fast.iloc[-1] > ema_slow.iloc[-1] and 42 <= rsi <= 70:
            return TradeProposal(
                symbol=symbol,
                direction="BUY",
                entry_price=round(price, 2),
                stop_loss=round(price - sl_dist, 2),
                take_profit=round(price + tp_dist, 2),
                stop_loss_points=round(sl_dist, 2),
                strategy=f"XAUUSD_EMA_RSI_{regime.regime}",
                confidence=round(min(0.95, 0.65 + (rsi - 50) / 100), 2)
            )
        elif ema_fast.iloc[-1] < ema_slow.iloc[-1] and 30 <= rsi <= 58:
            return TradeProposal(
                symbol=symbol,
                direction="SELL",
                entry_price=round(price, 2),
                stop_loss=round(price + sl_dist, 2),
                take_profit=round(price - tp_dist, 2),
                stop_loss_points=round(sl_dist, 2),
                strategy=f"XAUUSD_EMA_RSI_{regime.regime}",
                confidence=round(min(0.95, 0.65 + (50 - rsi) / 100), 2)
            )
        return None
