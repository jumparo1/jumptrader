import streamlit as st
import requests
import pandas as pd
import time
from credentials import get_binance_client

# ─── Config ─────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Binance AI Trade Radar", layout="wide")
st.title("📊 Binance Perpetuals Dashboard — v1")

EXCHANGE_INFO = "https://fapi.binance.com/fapi/v1/exchangeInfo"
TICKER_24H   = "https://fapi.binance.com/fapi/v1/ticker/24hr"
KLINES       = "https://fapi.binance.com/fapi/v1/klines"

# ─── Helpers ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_perpetual_symbols():
    data = requests.get(EXCHANGE_INFO).json()
    return [
        s["symbol"]
        for s in data["symbols"]
        if s["contractType"] == "PERPETUAL" and s["status"] == "TRADING"
    ]

def get_24h_stats(symbol):
    r = requests.get(f"{TICKER_24H}?symbol={symbol}").json()
    return {
        "symbol": symbol,
        "chg24h": float(r.get("priceChangePercent", 0)),
        "vol24h": float(r.get("quoteVolume", 0)),
        "lastPrice": float(r.get("lastPrice", 0)),
    }

def get_1h_change(symbol):
    params = {
        "symbol": symbol,
        "interval": "1h",
        "limit": 2  # last two candles
    }
    klines = requests.get(KLINES, params=params).json()
    if len(klines) < 2:
        return 0.0
    prev_close = float(klines[0][4])
    last_close = float(klines[1][4])
    return (last_close - prev_close) / prev_close * 100

def compute_signals(row):
    tags = []
    if row["vol24h"] > 500_000_000:
        tags.append("🔥 Volume Spike")
    if row["chg1h"] > 5:
        tags.append("📈 1H Gainer")
    if abs(row["chg24h"]) > 10:
        tags.append("⚠️ Volatile")
    return ", ".join(tags) if tags else "-"

# ─── UI Controls ────────────────────────────────────────────────────────────────
symbols = get_perpetual_symbols()
count   = st.slider("How many symbols to load?", min_value=10, max_value=len(symbols), value=100, step=10)
refresh = st.number_input("Auto-refresh interval (sec)", min_value=10, value=60, step=5)

# ─── Private API Demo ───────────────────────────────────────────────────────────
st.subheader("🔐 Private API Demo")
st.info("This section demonstrates how to use private Binance API endpoints.")

# Example of how to use private endpoints (commented out for safety)
if st.button("Test Private API Connection"):
    try:
        client = get_binance_client()
        st.success("✅ Successfully connected to Binance API!")
        
        # Uncomment the following lines to actually fetch your account data:
        # balance = client.futures_account_balance()
        # st.write("Futures Account Balance:", balance)
        
        st.info("🔒 Private API calls are commented out for safety. Uncomment in code to enable.")
        
    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.info("Make sure you have created a .env file with your BINANCE_API_KEY and BINANCE_API_SECRET")

# ─── Public Data Dashboard ─────────────────────────────────────────────────────
st.subheader("📊 Public Market Data")

placeholder = st.empty()

# ─── Main Loop ─────────────────────────────────────────────────────────────────
while True:
    with placeholder.container():
        st.info("Fetching data…")
        rows = []
        for sym in symbols[:count]:
            stats = get_24h_stats(sym)
            stats["chg1h"] = get_1h_change(sym)
            rows.append(stats)
            time.sleep(0.03)  # rate-limit friendly

        df = pd.DataFrame(rows)
        df["Signal"] = df.apply(compute_signals, axis=1)
        df = df.sort_values("chg24h", ascending=False)

        st.dataframe(df[["symbol","lastPrice","chg1h","chg24h","vol24h","Signal"]],
                     width=0, height=600)

    time.sleep(refresh)
