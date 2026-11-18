import os
from typing import Dict, List, Tuple
import pandas as pd

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

class DerivMT5Bridge:
    def __init__(self, magic_number: int = 800088):
        self.magic = magic_number
        self.connected = False
        self.mode = "DISCONNECTED"
        self.account_info: Dict = {}
        self.last_error: str = ""

    def connect(self, login: int, password: str, server: str, path: str = "") -> Tuple[bool, str]:
        if not MT5_AVAILABLE:
            return False, "MetaTrader5 package is not installed. Run 'pip install MetaTrader5'."

        if not path or not os.path.exists(path):
            possible_paths = [
                path,
                r"C:\Program Files\Deriv MetaTrader 5\terminal64.exe",
                r"C:\Program Files\MetaTrader 5\terminal64.exe",
                r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe"
            ]
            path = ""
            for p in possible_paths:
                if p and os.path.exists(p):
                    path = p
                    break

        init_args = {"path": path} if path and os.path.exists(path) else {}
        
        try:
            mt5.shutdown()
        except Exception:
            pass

        if not mt5.initialize(**init_args):
            err_code, err_desc = mt5.last_error()
            self.last_error = f"MT5 initialize failed [{err_code}]: {err_desc}"
            return False, self.last_error

        auth_ok = mt5.login(login=int(login), password=str(password), server=str(server))
        if not auth_ok:
            err_code, err_desc = mt5.last_error()
            self.last_error = f"MT5 Auth Failed [{err_code}]: {err_desc}. Check Login ID, Password, and Server."
            mt5.shutdown()
            return False, self.last_error

        info = mt5.account_info()
        if info is None:
            self.last_error = "Connected, but failed to retrieve account info."
            mt5.shutdown()
            return False, self.last_error

        self.connected = True
        self.mode = "LIVE_MT5_IPC"
        self.account_info = {
            "login": info.login,
            "server": info.server,
            "balance": float(info.balance),
            "equity": float(info.equity),
            "margin": float(info.margin),
            "margin_free": float(info.margin_free),
            "currency": info.currency,
            "margin_mode": "HEDGING" if info.margin_mode == 2 else "NETTING"
        }
        return True, f"Successfully connected to #{info.login} on [{info.server}] ({self.account_info['margin_mode']})"

    def disconnect(self):
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()
        self.connected = False
        self.mode = "DISCONNECTED"

    def get_account_snapshot(self) -> Dict:
        if not self.connected or not MT5_AVAILABLE:
            return {"balance": 8000.0, "equity": 8000.0, "profit": 0.0, "margin_free": 8000.0, "mode": "DISCONNECTED"}
        
        info = mt5.account_info()
        if info is None:
            return self.account_info
        
        return {
            "login": info.login,
            "server": info.server,
            "balance": float(info.balance),
            "equity": float(info.equity),
            "profit": float(info.profit),
            "margin_free": float(info.margin_free),
            "mode": self.mode
        }

    def get_market_bars(self, symbol: str, count: int = 80) -> Tuple[pd.DataFrame, float, float]:
        if not self.connected or not MT5_AVAILABLE:
            raise ConnectionError("MT5 Bridge is not connected.")

        if not mt5.symbol_select(symbol, True):
            for alt in [symbol, "GOLD", "XAUUSD.m", "XAUUSDmicro", "XAUUSD_i"]:
                if mt5.symbol_select(alt, True):
                    symbol = alt
                    break

        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, count)
        tick = mt5.symbol_info_tick(symbol)
        sym_info = mt5.symbol_info(symbol)

        if rates is None or len(rates) == 0 or tick is None:
            raise ValueError(f"Could not fetch market bars or ticks for '{symbol}'. Please ensure '{symbol}' is added to your MT5 Market Watch.")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        spread = float(sym_info.spread) if sym_info else 15.0
        point_val = float(sym_info.trade_tick_value / sym_info.trade_tick_size) if sym_info and sym_info.trade_tick_size > 0 else 1.0
        
        return df[["time", "open", "high", "low", "close"]], spread, point_val

    def get_open_positions(self) -> List[Dict]:
        if not self.connected or not MT5_AVAILABLE:
            return []
        positions = mt5.positions_get(magic=self.magic)
        if positions is None:
            return []
        
        out = []
        for p in positions:
            out.append({
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": "BUY" if p.type == 0 else "SELL",
                "volume": p.volume,
                "price_open": p.price_open,
                "price_current": p.price_current,
                "sl": p.sl,
                "tp": p.tp,
                "profit": round(p.profit, 2),
                "comment": p.comment
            })
        return out

    def execute_bracket_order(self, symbol: str, direction: str, volume: float, price: float, sl: float, tp: float, comment: str = "XAUUSD_AEGIS") -> Tuple[bool, str]:
        if not self.connected or not MT5_AVAILABLE:
            return False, "Not connected to MT5."

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return False, f"Could not retrieve tick for {symbol}"

        exec_price = tick.ask if direction == "BUY" else tick.bid
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "price": exec_price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 30,
            "magic": self.magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

        res = mt5.order_send(request)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            return True, f"XAUUSD Fill #{res.order}: {direction} {volume} {symbol} @ {exec_price}"
        
        err_code, err_desc = mt5.last_error()
        return False, f"XAUUSD Order Rejected [{err_code}]: {err_desc} (retcode: {res.retcode if res else 'None'})"

    def close_all_positions(self) -> int:
        if not self.connected or not MT5_AVAILABLE:
            return 0
        positions = mt5.positions_get(magic=self.magic) or []
        closed = 0
        for p in positions:
            tick = mt5.symbol_info_tick(p.symbol)
            if not tick:
                continue
            close_type = mt5.ORDER_TYPE_SELL if p.type == 0 else mt5.ORDER_TYPE_BUY
            close_price = tick.bid if p.type == 0 else tick.ask
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": p.symbol,
                "volume": p.volume,
                "type": close_type,
                "position": p.ticket,
                "price": close_price,
                "deviation": 30,
                "magic": self.magic,
                "comment": "XAUUSD_KILL",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            res = mt5.order_send(req)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                closed += 1
        return closed
