import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class BotConfig:
    login: int = int(os.getenv("MT5_LOGIN", "72839401") or 72839401)
    password: str = os.getenv("MT5_PASSWORD", "")
    server: str = os.getenv("MT5_SERVER", "Deriv-Demo")
    mt5_path: str = os.getenv("MT5_PATH", r"C:\Program Files\Deriv MetaTrader 5\terminal64.exe")
    account_capital: float = float(os.getenv("ACCOUNT_CAPITAL", "8000.0"))
    risk_per_trade_pct: float = float(os.getenv("RISK_PER_TRADE_PCT", "0.50"))
    max_daily_drawdown_pct: float = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "2.00"))
    symbol: str = "XAUUSD"
    magic_number: int = int(os.getenv("MAGIC_NUMBER", "800088"))
