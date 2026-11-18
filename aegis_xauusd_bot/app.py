import time
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config import BotConfig
from mt5_bridge import DerivMT5Bridge
from agents import RegimeContextAgent, QuantSignalAgent
from risk_governor import DeterministicRiskGovernor

st.set_page_config(
    page_title="AEGIS-XAUUSD // Gold Autonomous Terminal",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
    .stApp {
        background-color: #07090f;
        color: #d2daf2;
    }
    section[data-testid="stSidebar"] {
        background-color: #0c0f17;
        border-right: 1px solid rgba(255, 215, 0, 0.25);
    }
    h1, h2, h3 {
        color: #ffd700 !important;
        font-family: 'Segoe UI', Roboto, monospace;
        letter-spacing: 1px;
    }
    div[data-testid="stMetric"] {
        background-color: #101420;
        border: 1px solid rgba(255, 215, 0, 0.3);
        border-radius: 6px;
        padding: 12px 16px;
        box-shadow: 0 0 12px rgba(255, 215, 0, 0.08);
    }
    div[data-testid="stMetricValue"] {
        color: #ffd700 !important;
        font-family: monospace;
    }
    .agent-card {
        background: #101420;
        border: 1px solid rgba(255, 215, 0, 0.28);
        border-left: 4px solid #ffd700;
        border-radius: 6px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }
    .agent-title {
        color: #ffd700;
        font-weight: 700;
        font-size: 13px;
        letter-spacing: 0.8px;
    }
    .agent-sub {
        color: #8c9cb8;
        font-size: 12px;
        margin-top: 3px;
    }
    .stButton > button {
        border: 1px solid #ffd700;
        background-color: rgba(255, 215, 0, 0.1);
        color: #ffd700;
        font-weight: 600;
        border-radius: 4px;
    }
    .stButton > button:hover {
        background-color: #ffd700;
        color: #07090f;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

if "cfg" not in st.session_state:
    st.session_state.cfg = BotConfig()
if "bridge" not in st.session_state:
    st.session_state.bridge = DerivMT5Bridge(magic_number=st.session_state.cfg.magic_number)
if "regime_agent" not in st.session_state:
    st.session_state.regime_agent = RegimeContextAgent()
if "signal_agent" not in st.session_state:
    st.session_state.signal_agent = QuantSignalAgent()
if "risk_gov" not in st.session_state:
    st.session_state.risk_gov = DeterministicRiskGovernor(
        initial_balance=st.session_state.cfg.account_capital,
        risk_per_trade_pct=st.session_state.cfg.risk_per_trade_pct,
        max_daily_dd_pct=st.session_state.cfg.max_daily_drawdown_pct
    )
if "auto_trade" not in st.session_state:
    st.session_state.auto_trade = False
if "logs" not in st.session_state:
    st.session_state.logs = [f"[{datetime.now().strftime('%H:%M:%S')}] AEGIS-XAUUSD Terminal initialized. Locked strictly to Gold."]
if "equity_history" not in st.session_state:
    st.session_state.equity_history = []

def add_log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.insert(0, f"[{ts}] {msg}")
    st.session_state.logs = st.session_state.logs[:100]

if not st.session_state.bridge.connected and st.session_state.cfg.password:
    ok, msg = st.session_state.bridge.connect(
        login=st.session_state.cfg.login,
        password=st.session_state.cfg.password,
        server=st.session_state.cfg.server,
        path=st.session_state.cfg.mt5_path
    )
    add_log(msg)

AGENT_CARDS_HTML = """
<div class="agent-card">
    <div class="agent-title">01. GOLD REGIME AGENT</div>
    <div class="agent-sub">ATR Spread & Volatility Filter</div>
</div>
<div class="agent-card">
    <div class="agent-title">02. XAUUSD QUANT SIGNAL</div>
    <div class="agent-sub">EMA 9/21 + RSI + Gold Brackets</div>
</div>
<div class="agent-card">
    <div class="agent-title">03. GOLD RISK GOVERNOR</div>
    <div class="agent-sub">Hard Veto | 0.5% Risk | 2% Daily DD</div>
</div>
<div class="agent-card">
    <div class="agent-title">04. XAUUSD RECONCILER</div>
    <div class="agent-sub">Direct MetaTrader 5 Execution</div>
</div>
"""

with st.sidebar:
    st.markdown("## 🪙 AEGIS-XAUUSD CORE")
    snap = st.session_state.bridge.get_account_snapshot()
    status_color = "#00ff66" if st.session_state.bridge.connected else "#ff3366"
    st.markdown(f"**Gateway:** <span style='color:{status_color}'>{snap.get('mode')}</span>", unsafe_allow_html=True)
    st.markdown(f"**Account:** `{snap.get('login', 'N/A')}` @ `{snap.get('server', 'Deriv-Demo')}`")
    st.markdown(f"**Target Instrument:** `XAUUSD (Gold)`")

    st.divider()
    st.session_state.auto_trade = st.toggle("🪙 XAUUSD AUTONOMOUS TRADING", value=st.session_state.auto_trade)

    if st.button("🚨 EMERGENCY KILL SWITCH", use_container_width=True):
        st.session_state.auto_trade = False
        st.session_state.risk_gov.engage_kill_switch()
        closed = st.session_state.bridge.close_all_positions()
        add_log(f"EMERGENCY KILL SWITCH ENGAGED! Closed {closed} XAUUSD positions & locked execution.")

    if st.session_state.risk_gov.kill_switch_engaged:
        if st.button("🔓 Reset Circuit Breaker", use_container_width=True):
            st.session_state.risk_gov.reset_kill_switch(snap["balance"])
            add_log("Circuit breaker reset by operator.")

    st.divider()
    st.markdown("### 4-Agent Pipeline")
    st.markdown(AGENT_CARDS_HTML, unsafe_allow_html=True)

st.markdown("# AEGIS-XAUUSD // DEDICATED GOLD TRADING COMMAND CENTER")

tab_dash, tab_settings, tab_logs = st.tabs([
    "📊 Live Gold Dashboard",
    "⚙️ MT5 Login & Credentials",
    "📜 System Audit Logs"
])

market_connected = False
df_bars = pd.DataFrame()
spread_pts, point_val = 15.0, 1.0

if st.session_state.bridge.connected:
    try:
        df_bars, spread_pts, point_val = st.session_state.bridge.get_market_bars("XAUUSD", count=80)
        market_connected = True
    except Exception as e:
        try:
            df_bars, spread_pts, point_val = st.session_state.bridge.get_market_bars("GOLD", count=80)
            market_connected = True
        except Exception as e2:
            market_connected = False

regime_state = st.session_state.regime_agent.evaluate(df_bars, spread_pts) if market_connected else None
open_positions = st.session_state.bridge.get_open_positions() if st.session_state.bridge.connected else []
snap = st.session_state.bridge.get_account_snapshot()

if st.session_state.auto_trade and market_connected and st.session_state.bridge.connected:
    proposal = st.session_state.signal_agent.generate_signal("XAUUSD", df_bars, regime_state)
    if proposal:
        verdict = st.session_state.risk_gov.evaluate_trade(
            current_equity=snap["equity"],
            stop_loss_points=proposal.stop_loss_points,
            point_value=point_val,
            open_positions=open_positions
        )
        if verdict.approved:
            ok, exec_msg = st.session_state.bridge.execute_bracket_order(
                symbol="XAUUSD",
                direction=proposal.direction,
                volume=verdict.lot_size,
                price=proposal.entry_price,
                sl=proposal.stop_loss,
                tp=proposal.take_profit,
                comment=proposal.strategy[:24]
            )
            add_log(f"{verdict.reason} -> {exec_msg}")
            open_positions = st.session_state.bridge.get_open_positions()
        else:
            add_log(verdict.reason)

with tab_dash:
    _, dd_pct = st.session_state.risk_gov.check_daily_drawdown(snap["equity"])
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Account Balance", f"${snap['balance']:,.2f}")
    c2.metric("Live Equity", f"${snap['equity']:,.2f}", f"{snap.get('profit', 0.0):+.2f} USD")
    c3.metric("Gold Regime", regime_state.regime if regime_state else "DISCONNECTED", f"ATR {regime_state.atr_percentile:.0f}%" if regime_state else "N/A")
    c4.metric("Daily Drawdown", f"{dd_pct:.2f}%", f"Max {st.session_state.risk_gov.max_daily_dd_pct:.1f}%", delta_color="inverse")
    c5.metric("Active XAUUSD Legs", f"{len(open_positions)} / 3", "XAUUSD")

    col_chart, col_book = st.columns([2, 1])

    with col_chart:
        st.markdown("### Live XAUUSD (Gold) Price & Volatility Stream")
        if market_connected:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_bars["time"],
                y=df_bars["close"],
                mode="lines",
                name="XAUUSD",
                line=dict(color="#ffd700", width=2.2),
                fill="tozeroy",
                fillcolor="rgba(255, 215, 0, 0.08)"
            ))
            fig.add_trace(go.Scatter(
                x=df_bars["time"],
                y=df_bars["close"].ewm(span=9).mean(),
                mode="lines",
                name="EMA 9",
                line=dict(color="#00ff66", width=1.2, dash="dot")
            ))
            fig.add_trace(go.Scatter(
                x=df_bars["time"],
                y=df_bars["close"].ewm(span=21).mean(),
                mode="lines",
                name="EMA 21",
                line=dict(color="#ff3366", width=1.2, dash="dash")
            ))
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#101420",
                plot_bgcolor="#101420",
                height=360,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(showgrid=True, gridcolor="rgba(255,215,0,0.06)"),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,215,0,0.06)"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ MT5 not connected or XAUUSD not found in Market Watch. Please enter your credentials in the Settings tab and ensure XAUUSD is added to your MT5 Market Watch.")

    with col_book:
        st.markdown("### Active XAUUSD Positions")
        if open_positions:
            pos_df = pd.DataFrame(open_positions)[["ticket", "type", "volume", "price_open", "sl", "tp", "profit"]]
            st.dataframe(pos_df, use_container_width=True, hide_index=True, height=260)
            if st.button("Close All XAUUSD Positions", use_container_width=True):
                closed = st.session_state.bridge.close_all_positions()
                add_log(f"Manual square-off executed: closed {closed} XAUUSD positions.")
                st.rerun()
        else:
            st.info("No active XAUUSD trades. Connect MT5 and enable autonomous trading.")

        st.markdown("### Live Telemetry Feed")
        st.code("\n".join(st.session_state.logs[:8]), language="text")

with tab_settings:
    st.markdown("### MetaTrader 5 Account & Credential Configuration")
    st.caption("Fixing error [-6] Authorization Failed: Verify your exact MetaTrader 5 Login ID, Master Password, and Broker Server name below.")

    with st.form("mt5_credentials_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            in_login = st.text_input("MT5 Login ID (Numeric)", value=str(st.session_state.cfg.login))
            in_password = st.text_input("MT5 Master Password", value=st.session_state.cfg.password, type="password")
            in_server = st.text_input("Broker Server (e.g. Deriv-Demo)", value=st.session_state.cfg.server)
        with col_b:
            in_path = st.text_input("MT5 Terminal Executable Path", value=st.session_state.cfg.mt5_path)
            in_risk = st.slider("Risk Per XAUUSD Trade (%)", min_value=0.10, max_value=2.00, value=float(st.session_state.cfg.risk_per_trade_pct), step=0.05)
            in_dd = st.slider("Daily Drawdown Circuit Breaker (%)", min_value=0.50, max_value=5.00, value=float(st.session_state.cfg.max_daily_drawdown_pct), step=0.25)

        submitted = st.form_submit_button("🔌 Connect & Authenticate MT5")
        if submitted:
            login_int = int(in_login) if in_login.isdigit() else 72839401
            st.session_state.cfg.login = login_int
            st.session_state.cfg.password = in_password
            st.session_state.cfg.server = in_server
            st.session_state.cfg.mt5_path = in_path
            st.session_state.cfg.risk_per_trade_pct = in_risk
            st.session_state.cfg.max_daily_drawdown_pct = in_dd

            st.session_state.risk_gov.risk_per_trade_pct = in_risk
            st.session_state.risk_gov.max_daily_dd_pct = in_dd

            with open(".env", "w", encoding="utf-8") as f:
                f.write(f"MT5_LOGIN={login_int}\n")
                f.write(f"MT5_PASSWORD={in_password}\n")
                f.write(f"MT5_SERVER={in_server}\n")
                f.write(f"MT5_PATH={in_path}\n")
                f.write(f"ACCOUNT_CAPITAL={st.session_state.cfg.account_capital}\n")
                f.write(f"RISK_PER_TRADE_PCT={in_risk}\n")
                f.write(f"MAX_DAILY_DRAWDOWN_PCT={in_dd}\n")
                f.write(f"SYMBOL=XAUUSD\n")
                f.write(f"MAGIC_NUMBER=800088\n")

            ok, conn_msg = st.session_state.bridge.connect(
                login=login_int,
                password=in_password,
                server=in_server,
                path=in_path
            )
            add_log(conn_msg)
            if ok:
                st.success(conn_msg)
            else:
                st.error(conn_msg)

with tab_logs:
    st.markdown("### Immutable Execution Audit Trail")
    st.code("\n".join(st.session_state.logs), language="text")

time.sleep(2)
st.rerun()
