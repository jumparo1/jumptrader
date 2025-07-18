import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import logging
import asyncio
import threading
import json
import os
from clients.ws_client import WebSocketClient
from clients.orion_cli import fetch_orion_data, test_orion_cli
from clients.binance import get_btc_correlation
from clients.coingecko import fetch_coingecko_data
from signals.basic import compute_comprehensive_signals

# Add chatbot imports
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from mentorship.embed_store import ingest_transcript, query_store, get_store_stats, clear_store

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize WebSocket queue and tick storage
if 'tick_queue' not in st.session_state:
    st.session_state.tick_queue = None
    
if 'ticks' not in st.session_state:
    st.session_state.ticks = {}
    
if 'ws_started' not in st.session_state:
    st.session_state.ws_started = False

# Page config
st.set_page_config(
    page_title="JumpTrader - AI Trading Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ratio tracking configuration
RATIO_CACHE_PATH = "data/ratio_cache.json"
SPIKE_THRESHOLD = 10  # percent points for ratio spike detection

# Load previous ratios if file exists
def load_previous_ratios():
    """Load previous Circ/FDV ratios from cache file."""
    try:
        if os.path.exists(RATIO_CACHE_PATH):
            with open(RATIO_CACHE_PATH, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading ratio cache: {e}")
    return {}

def save_current_ratios(ratios):
    """Save current Circ/FDV ratios to cache file."""
    try:
        os.makedirs(os.path.dirname(RATIO_CACHE_PATH), exist_ok=True)
        with open(RATIO_CACHE_PATH, "w") as f:
            json.dump(ratios, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving ratio cache: {e}")

def detect_ratio_spike(current_ratio, previous_ratio, threshold=SPIKE_THRESHOLD):
    """Detect if there's a significant change in the Circ/FDV ratio."""
    if previous_ratio is None or current_ratio == 0:
        return None
    
    change = current_ratio - previous_ratio
    if abs(change) >= threshold:
        direction = "🔺" if change > 0 else "🔻"
        return f"{direction} {change:+.1f}%"
    return None

# Binance API endpoints
BINANCE_BASE_URL = "https://fapi.binance.com"
EXCHANGE_INFO_URL = f"{BINANCE_BASE_URL}/fapi/v1/exchangeInfo"
TICKER_24H_URL = f"{BINANCE_BASE_URL}/fapi/v1/ticker/24hr"
KLINES_URL = f"{BINANCE_BASE_URL}/fapi/v1/klines"

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_perpetual_symbols():
    """Get all perpetual trading symbols from Binance."""
    try:
        response = requests.get(EXCHANGE_INFO_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        symbols = [
            symbol["symbol"] for symbol in data["symbols"]
            if symbol["contractType"] == "PERPETUAL" and symbol["status"] == "TRADING"
        ]
        logger.info(f"Found {len(symbols)} perpetual symbols")
        return symbols
    except Exception as e:
        logger.error(f"Error fetching symbols: {e}")
        return []

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_24h_ticker_data(symbol):
    """Get 24h ticker data for a symbol."""
    try:
        response = requests.get(f"{TICKER_24H_URL}?symbol={symbol}", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        return {
            "symbol": symbol,
            "lastPrice": float(data.get("lastPrice", 0)),
            "priceChangePercent": float(data.get("priceChangePercent", 0)),
            "volume": float(data.get("volume", 0)),
            "quoteVolume": float(data.get("quoteVolume", 0)),
            "highPrice": float(data.get("highPrice", 0)),
            "lowPrice": float(data.get("lowPrice", 0)),
            "openPrice": float(data.get("openPrice", 0)),
            "count": int(data.get("count", 0))
        }
    except Exception as e:
        logger.error(f"Error fetching ticker for {symbol}: {e}")
        return None

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_klines_data(symbol, interval="1h", limit=2):
    """Get klines/candlestick data for a symbol."""
    try:
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        response = requests.get(KLINES_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if len(data) >= 2:
            prev_close = float(data[0][4])  # Previous close
            last_close = float(data[1][4])  # Current close
            change_1h = ((last_close - prev_close) / prev_close) * 100
            return change_1h
        return 0.0
    except Exception as e:
        logger.error(f"Error fetching klines for {symbol}: {e}")
        return 0.0

def compute_signals(row):
    """Compute trading signals based on data."""
    signals = []
    
    # Volume spike signal
    if row["quoteVolume"] > 500_000_000:  # 500M volume
        signals.append("🔥 Volume Spike")
    
    # 1h momentum signal
    if row["change_1h"] > 3:
        signals.append("📈 1H Bullish")
    elif row["change_1h"] < -3:
        signals.append("📉 1H Bearish")
    
    # 24h volatility signal
    if abs(row["priceChangePercent"]) > 10:
        signals.append("⚠️ High Volatility")
    
    # Price action signals
    if row["lastPrice"] > row["highPrice"] * 0.99:
        signals.append("🚀 Near High")
    elif row["lastPrice"] < row["lowPrice"] * 1.01:
        signals.append("📉 Near Low")
    
    # Real-time tick signals
    if "last_tick_price" in row and row["last_tick_price"] and row["last_tick_price"] > 0:
        tick_change = ((row["last_tick_price"] - row["lastPrice"]) / row["lastPrice"]) * 100
        if abs(tick_change) > 0.5:  # 0.5% tick change
            signals.append("⚡ Tick Spike")
    
    return ", ".join(signals) if signals else "-"

def start_websocket_client(symbols):
    """Start WebSocket client in a separate thread."""
    if not st.session_state.ws_started:
        try:
            # Use the provided symbols (already sorted by tickCount)
            ws_symbols = symbols[:10]  # Limit to top 10 for WebSocket performance
            # Create queue in the thread with event loop
            if st.session_state.tick_queue is None:
                st.session_state.tick_queue = asyncio.Queue()
            client = WebSocketClient(ws_symbols, st.session_state.tick_queue)
            
            def run_websocket():
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(client.run())
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                finally:
                    loop.close()
            
            thread = threading.Thread(target=run_websocket, daemon=True)
            thread.start()
            st.session_state.ws_started = True
            st.session_state.ws_client = client
            logger.info(f"WebSocket client started for {len(ws_symbols)} symbols")
        except Exception as e:
            logger.error(f"Failed to start WebSocket client: {e}")

def consume_ticks():
    """Consume ticks from the queue and update session state."""
    try:
        if st.session_state.tick_queue is not None:
            while not st.session_state.tick_queue.empty():
                tick = st.session_state.tick_queue.get_nowait()
                sym = tick["symbol"]
                st.session_state.ticks[sym] = {
                    "last_tick_price": tick["price"],
                    "tick_volume": tick["qty"],
                    "tick_timestamp": tick["timestamp"]
                }
    except Exception as e:
        logger.error(f"Error consuming ticks: {e}")

@st.cache_data(ttl=15)
def get_orion_snapshot(symbols=None):
    try:
        return fetch_orion_data(symbols)
    except Exception as e:
        logger.error(f"Error fetching Orion data: {e}")
        return {}

@st.cache_data(ttl=60)
def get_coingecko_snapshot(symbols):
    try:
        return fetch_coingecko_data(symbols)
    except Exception as e:
        logger.error(f"Error fetching CoinGecko data: {e}")
        return {}

def get_market_data(symbol_limit=10, spike_threshold=10):
    """
    Get market data for the specified number of symbols.
    
    Args:
        symbol_limit: Number of symbols to fetch
        spike_threshold: Threshold for ratio spike detection
        
    Returns:
        DataFrame with market data
    """
    # Get symbols
    symbols = get_perpetual_symbols()
    if not symbols:
        return pd.DataFrame()
    
    # Test and fetch Orion CLI data for all symbols first
    orion_available = test_orion_cli()
    
    if orion_available:
        # Fetch Orion data for all symbols to get tickCount for sorting
        orion_data = get_orion_snapshot(symbols)
        st.session_state.orion_data = orion_data
        logger.info(f"Orion CLI data loaded: {len(orion_data)} symbols")
        
        # Filter symbols to only those with Orion data and tickCount > 0
        symbols_with_orion = [
            s for s in symbols 
            if s in orion_data and orion_data[s].get("tickCount", 0) > 0
        ]
        
        # Sort symbols by tickCount from Orion data, descending
        symbols_sorted = sorted(
            symbols_with_orion,
            key=lambda s: orion_data[s].get("tickCount", 0),
            reverse=True
        )
        
        # Select top N symbols by tickCount
        top_symbols = symbols_sorted[:symbol_limit]
        logger.info(f"Selected top {len(top_symbols)} symbols by tickCount from {len(symbols_with_orion)} available")
        
        # Log the selected symbols and their tickCounts for debugging
        for i, symbol in enumerate(top_symbols):
            tick_count = orion_data[symbol].get("tickCount", 0)
            logger.info(f"  {i+1}. {symbol}: {tick_count} ticks")
    else:
        st.session_state.orion_data = {}
        logger.warning("Orion CLI not available, using first N symbols")
        top_symbols = symbols[:symbol_limit]
    
    # Start WebSocket client for real-time ticks with top symbols
    start_websocket_client(top_symbols)
    
    # Consume any available ticks
    consume_ticks()
    
    # Fetch CoinGecko data for the selected symbols
    coingecko = get_coingecko_snapshot(top_symbols)
    
    # Load previous ratios for spike detection
    previous_ratios = load_previous_ratios()
    current_ratios = {}
    
    market_data = []
    
    for i, symbol in enumerate(top_symbols):
        logger.info(f"Processing symbol {i+1}/{len(top_symbols)}: {symbol}")
        
        try:
            # Get ticker data
            logger.info(f"Fetching ticker data for {symbol}")
            ticker_data = get_24h_ticker_data(symbol)
            if not ticker_data:
                logger.warning(f"No ticker data for {symbol}, skipping")
                continue
                
            # Get 1h change
            logger.info(f"Fetching 1h change for {symbol}")
            change_1h = get_klines_data(symbol, "1h", 2)
            
            # Get real-time tick data
            tick_info = st.session_state.ticks.get(symbol, {})
            last_tick_price = tick_info.get("last_tick_price", 0.0)
            tick_volume = tick_info.get("tick_volume", 0.0)
            
            # Ensure numeric values
            try:
                last_tick_price = float(last_tick_price) if last_tick_price else 0.0
                tick_volume = float(tick_volume) if tick_volume else 0.0
            except (ValueError, TypeError):
                last_tick_price = 0.0
                tick_volume = 0.0
            
            # Get Orion CLI data
            orion_info = st.session_state.orion_data.get(symbol, {})
            tick_count = orion_info.get("tickCount", 0)
            funding_rate = float(orion_info.get("fundingRate", 0))
            open_interest = float(orion_info.get("openInterest", 0))
            
            # Get BTC correlation
            logger.info(f"Fetching BTC correlation for {symbol}")
            btc_corr = get_btc_correlation(symbol)
            
            # Get CoinGecko data
            cg = coingecko.get(symbol, {})
            mcap = cg.get("market_cap", 0.0)
            fdv = cg.get("fdv", 0.0)
            
            # Calculate circulating market cap vs. FDV ratio
            ratio = (mcap / fdv) if fdv > 0 else 0.0
            
            # Store current ratio for cache
            current_ratios[symbol] = ratio
            
            # Detect ratio spike
            prev_ratio = previous_ratios.get(symbol)
            ratio_spike = detect_ratio_spike(ratio, prev_ratio, spike_threshold)
            
            # Combine data
            row_data = {
                **ticker_data,
                "change_1h": change_1h,
                "btc_corr": btc_corr,
                "last_tick_price": last_tick_price,
                "tick_volume": tick_volume,
                "tickCount": tick_count,
                "fundingRate": funding_rate,
                "openInterest": open_interest,
                "cg_market_cap": mcap,
                "cg_fdv": fdv,
                "circ_fdv_ratio": ratio,
                "ratio_spike": ratio_spike
            }
            
            # Compute signals
            row_data["signals"] = compute_signals(row_data)
            
            market_data.append(row_data)
            logger.info(f"Successfully processed {symbol}")
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            continue
        
        # Minimal delay for faster loading with fewer symbols
        time.sleep(0.01)
    
    # Save current ratios for next comparison
    save_current_ratios(current_ratios)
    
    if market_data:
        # Convert to DataFrame
        df = pd.DataFrame(market_data)
        
        # Keep order by tickCount (already sorted in top_symbols)
        
        # Format display columns
        display_df = df[[
            "symbol", "lastPrice", "change_1h", "btc_corr", "priceChangePercent", 
            "quoteVolume", "cg_market_cap", "cg_fdv", "circ_fdv_ratio", "ratio_spike", "tickCount", "fundingRate", "openInterest", "signals"
        ]].copy()
        
        # Format numbers
        display_df["lastPrice"] = display_df["lastPrice"].round(4)
        display_df["change_1h"] = display_df["change_1h"].round(2)
        display_df["btc_corr"] = display_df["btc_corr"].round(2)
        display_df["priceChangePercent"] = display_df["priceChangePercent"].round(2)
        display_df["quoteVolume"] = (display_df["quoteVolume"] / 1_000_000).round(1)  # Convert to millions
        display_df["cg_market_cap"] = (display_df["cg_market_cap"] / 1_000_000_000).round(2)  # Convert to billions
        display_df["cg_fdv"] = (display_df["cg_fdv"] / 1_000_000_000).round(2)  # Convert to billions
        display_df["circ_fdv_ratio"] = (display_df["circ_fdv_ratio"] * 100).round(1)  # Convert to percentage
        
        # Format Orion data
        display_df["tickCount"] = display_df["tickCount"].astype(int)
        display_df["fundingRate"] = (display_df["fundingRate"] * 100).round(4)  # Convert to percentage
        display_df["openInterest"] = (display_df["openInterest"] / 1_000_000).round(1)  # Convert to millions
        
        # Rename columns for display
        display_df = display_df.rename(columns={
            "change_1h":         "chg1h (%)",
            "priceChangePercent": "chg24h (%)",
            "quoteVolume":       "vol24h",
            "cg_market_cap":     "CG MCAP (B)",
            "cg_fdv":            "FDV (B)",
            "circ_fdv_ratio":    "Circ/FDV (%)",
            "ratio_spike":       "Ratio Spike",
            "signals":           "Signal"
        })
        
        # Drop the duplicate count.1 column if it exists
        if "count.1" in display_df.columns:
            display_df = display_df.drop(columns=["count.1"])
        
        return display_df, df  # Return both formatted and raw dataframes
    
    return pd.DataFrame(), pd.DataFrame()

def main():
    # Header
    st.title("🚀 JumpTrader - AI Trading Dashboard")
    st.markdown("Real-time Binance Perpetuals with AI-Powered Signals")
    
    # Sidebar controls
    st.sidebar.header("⚙️ Dashboard Controls")
    
    # Get symbols
    symbols = get_perpetual_symbols()
    if not symbols:
        st.error("Failed to fetch symbols from Binance")
        return
    
    # Symbol limit control
    symbol_limit = st.sidebar.slider(
        "Number of symbols to display",
        min_value=3,
        max_value=min(20, len(symbols)),
        value=5,
        step=1
    )
    
    # Ratio spike detection settings
    st.sidebar.header("📊 Ratio Spike Detection")
    spike_threshold = st.sidebar.slider(
        "Spike threshold (%)",
        min_value=1,
        max_value=50,
        value=10,
        step=1,
        help="Minimum percentage change in Circ/FDV ratio to trigger a spike alert"
    )
    
    st.sidebar.info("""
    **Ratio Spike Alerts:**
    - 🔺 **Green**: Circ/FDV ratio increased (more tokens circulating)
    - 🔻 **Red**: Circ/FDV ratio decreased (fewer tokens circulating)
    
    **What it means:**
    - **Token unlocks** (ratio increases)
    - **New token emissions** (ratio decreases)
    - **Market cap changes** vs. FDV
    """)
    
    # Status indicators
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("🔗 Connection", "✅ Connected")
    
    with col2:
        st.metric("📊 Symbols Available", f"{symbol_limit}/{len(symbols)}")
    
    with col3:
        st.metric("🕒 Last Update", datetime.now().strftime("%H:%M:%S"))
        
    with col4:
        ws_status = "🟢 Active" if st.session_state.ws_started else "🔴 Inactive"
        tick_count = len(st.session_state.ticks)
        st.metric("📡 WebSocket", f"{ws_status} ({tick_count} ticks)")
        
    with col5:
        orion_status = "🟢 Active" if st.session_state.get('orion_data', {}) else "🔴 Inactive"
        orion_count = len(st.session_state.get('orion_data', {}))
        st.metric("🔧 Orion CLI", f"{orion_status} ({orion_count} symbols)")
    
    # Fetch market data
    with st.spinner("Fetching market data..."):
        display_df, raw_df = get_market_data(symbol_limit, spike_threshold)
    
    if display_df.empty:
        st.error("No market data available. Please check your connection.")
        return
    
    # Create three tabs
    tabs = st.tabs(["📈 Main Dashboard", "🚨 Signal Dashboard", "🔥 Chat Agent"])
    main_tab, signal_tab, chat_tab = tabs
    
    with main_tab:
        st.subheader("📈 Main Market Data")
        
        # Style: color 1H % and highlight ratio spikes
        def highlight_spikes(val):
            if pd.isna(val) or val is None:
                return ""
            if "🔺" in str(val):
                return "background-color: #d4edda; color: #155724; font-weight: bold;"
            elif "🔻" in str(val):
                return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
            return ""
        
        styled = display_df.style.map(
            lambda v: "color: green;" if v > 0 else "color: red;",
            subset=["chg1h (%)"]
        ).map(
            highlight_spikes,
            subset=["Ratio Spike"]
        ).format({
            "BTC Corr": "{:.2f}",
            "CG MCAP (B)": "{:.2f}",
            "FDV (B)": "{:.2f}",
            "Circ/FDV (%)": "{:.1f}%"
        })
        
        st.dataframe(styled, use_container_width=True, height=600)
    
    with signal_tab:
        st.subheader("🚨 Signal Dashboard")
        
        # Apply compute_comprehensive_signals to each row
        signal_results = raw_df.apply(lambda row: compute_comprehensive_signals(row), axis=1)
        
        # Convert list of dicts to DataFrame
        signal_df = pd.DataFrame(list(signal_results))
        
        # Add a boolean column for whether any signals were detected
        signal_df["has_signal"] = signal_df["count"] > 0
        
        # Merge with original data for context
        merged = pd.concat([raw_df.reset_index(drop=True), signal_df], axis=1)
        
        # Filter for rows with signals
        filtered = merged[merged["has_signal"] == True]
        
        if not filtered.empty:
            # Get available columns and select the ones we want
            available_columns = filtered.columns.tolist()
            desired_columns = [
                "symbol", "lastPrice", "change_1h", "btc_corr", "priceChangePercent", 
                "quoteVolume", "cg_market_cap", "cg_fdv", "circ_fdv_ratio", "ratio_spike", 
                "tickCount", "fundingRate", "openInterest", "signal_string", "count"
            ]
            
            # Only select columns that exist
            existing_columns = [col for col in desired_columns if col in available_columns]
            signal_display = filtered[existing_columns].copy()
            
            # Apply direct DataFrame renaming
            signal_display = signal_display.rename(columns={
                "change_1h":           "1H %",
                "btc_corr":            "BTC Corr",
                "priceChangePercent":  "24H %",
                "quoteVolume":         "Vol 24H",
                "cg_market_cap":       "CG MCAP (B)",
                "cg_fdv":              "FDV (B)",
                "circ_fdv_ratio":      "Circ/FDV %",
                "ratio_spike":         "Ratio Spike",
                "signal_string":       "Signals",
                "count":               "Signal Count"
            })
            
            # Drop the duplicate count.1 column if it exists
            if "count.1" in signal_display.columns:
                signal_display = signal_display.drop(columns=["count.1"])
            
            # Format numbers for columns that exist
            if "lastPrice" in signal_display.columns:
                signal_display["lastPrice"] = signal_display["lastPrice"].round(4)
            if "change_1h" in signal_display.columns:
                signal_display["change_1h"] = signal_display["change_1h"].round(2)
            if "btc_corr" in signal_display.columns:
                signal_display["btc_corr"] = signal_display["btc_corr"].round(2)
            if "priceChangePercent" in signal_display.columns:
                signal_display["priceChangePercent"] = signal_display["priceChangePercent"].round(2)
            if "quoteVolume" in signal_display.columns:
                signal_display["quoteVolume"] = (signal_display["quoteVolume"] / 1_000_000).round(1)
            if "cg_market_cap" in signal_display.columns:
                signal_display["cg_market_cap"] = (signal_display["cg_market_cap"] / 1_000_000_000).round(2)
            if "cg_fdv" in signal_display.columns:
                signal_display["cg_fdv"] = (signal_display["cg_fdv"] / 1_000_000_000).round(2)
            if "circ_fdv_ratio" in signal_display.columns:
                signal_display["circ_fdv_ratio"] = (signal_display["circ_fdv_ratio"] * 100).round(1)
            if "tickCount" in signal_display.columns:
                signal_display["tickCount"] = signal_display["tickCount"].astype(int)
            if "fundingRate" in signal_display.columns:
                signal_display["fundingRate"] = (signal_display["fundingRate"] * 100).round(4)
            if "openInterest" in signal_display.columns:
                signal_display["openInterest"] = (signal_display["openInterest"] / 1_000_000).round(1)
            
            # ✅ Deduplicate columns if needed
            def deduplicate_columns(columns):
                seen = {}
                new_cols = []
                for col in columns:
                    if col not in seen:
                        seen[col] = 0
                        new_cols.append(col)
                    else:
                        seen[col] += 1
                        new_cols.append(f"{col}.{seen[col]}")
                return new_cols

            # Check for and handle duplicate columns
            if len(signal_display.columns) != len(set(signal_display.columns)):
                signal_display.columns = deduplicate_columns(signal_display.columns.tolist())
            
            # Style the signal dashboard
            signal_styled = signal_display.style
            
            # Apply color styling to 1H % if it exists
            if "1H %" in signal_display.columns:
                signal_styled = signal_styled.map(
                    lambda v: "color: green;" if v > 0 else "color: red;",
                    subset=["1H %"]
                )
            
            # Apply spike highlighting if Ratio Spike exists
            if "Ratio Spike" in signal_display.columns:
                signal_styled = signal_styled.map(
                    highlight_spikes,
                    subset=["Ratio Spike"]
                )
            
            # Apply formatting for columns that exist
            format_dict = {}
            if "BTC Corr" in signal_display.columns:
                format_dict["BTC Corr"] = "{:.2f}"
            if "CG MCAP (B)" in signal_display.columns:
                format_dict["CG MCAP (B)"] = "{:.2f}"
            if "FDV (B)" in signal_display.columns:
                format_dict["FDV (B)"] = "{:.2f}"
            if "Circ/FDV %" in signal_display.columns:
                format_dict["Circ/FDV %"] = "{:.1f}%"
            if "Signal Count" in signal_display.columns:
                format_dict["Signal Count"] = "{:.0f}"
            
            if format_dict:
                signal_styled = signal_styled.format(format_dict)
            
            st.dataframe(signal_styled, use_container_width=True, height=600)
        else:
            st.info("No signals detected in the current data. Try adjusting the symbol limit or check market conditions.")
    
    with chat_tab:
        st.header("🔥 AI Mentor Chat Agent")
        st.markdown("**Spicy** is your AI mentor trained on your trading lessons. Ask anything about trading strategies, risk management, or market analysis!")
        
        # Initialize session state for chat
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        
        if "spicy_personality" not in st.session_state:
            st.session_state.spicy_personality = {
                "name": "Spicy",
                "style": "Direct, experienced, and slightly edgy",
                "greeting": "Hey trader! I'm Spicy, your AI mentor. I've learned from your lessons and I'm here to help you level up your trading game. What's on your mind?"
            }
        
        # Auto-load sample transcript on first run
        if "transcript_loaded" not in st.session_state:
            try:
                transcript_path = "sample_transcript.txt"
                if os.path.exists(transcript_path):
                    with open(transcript_path, 'r', encoding='utf-8') as f:
                        transcript_text = f.read()
                    
                    if ingest_transcript(transcript_text, "sample_lessons"):
                        st.session_state.transcript_loaded = True
                        st.success("✅ Loaded lessons into Spicy's memory!")
                    else:
                        st.warning("⚠️ Failed to load sample transcript")
                else:
                    st.warning("⚠️ sample_transcript.txt not found")
            except Exception as e:
                st.error(f"Error loading transcript: {e}")
            st.session_state.transcript_loaded = True
        
        # Sidebar for Spicy's info
        with st.sidebar:
            st.header("🔥 Spicy's Corner")
            st.markdown("### 🤖 **Spicy** - AI Trading Mentor")
            st.markdown("*Direct, experienced, and slightly edgy*")
            
            # Knowledge base stats
            stats = get_store_stats()
            st.metric("📚 Lessons Learned", stats["total_documents"])
            st.metric("🧠 Knowledge Chunks", stats["total_chunks"])
            
            if stats["total_documents"] > 0:
                st.success("✅ Spicy is ready to help!")
            else:
                st.warning("⚠️ Spicy needs to learn first!")
            
            st.markdown("---")
            
            # Quick actions
            if st.button("🗑️ Clear Spicy's Memory", type="secondary"):
                if clear_store():
                    st.success("Spicy's memory cleared!")
                    st.rerun()
                else:
                    st.error("Failed to clear memory")
        
        # Welcome message if no chat history
        if not st.session_state.chat_history:
            st.info(f"🔥 **{st.session_state.spicy_personality['greeting']}**")
        
        # Display chat history
        if st.session_state.chat_history:
            st.markdown("### 📝 Conversation History")
            
            for i, (question, answer, excerpts) in enumerate(st.session_state.chat_history):
                # User message
                with st.container():
                    col1, col2 = st.columns([1, 20])
                    with col1:
                        st.markdown("👤")
                    with col2:
                        st.markdown(f"**You:** {question}")
                
                # Spicy's response
                with st.container():
                    col1, col2 = st.columns([1, 20])
                    with col1:
                        st.markdown("🔥")
                    with col2:
                        st.markdown(f"**Spicy:** {answer}")
                        
                        # Show relevant excerpts in expandable section
                        if excerpts:
                            with st.expander(f"📖 View {len(excerpts)} relevant lesson excerpts", expanded=False):
                                for j, excerpt in enumerate(excerpts, 1):
                                    st.markdown(f"**{j}.** {excerpt[:300]}...")
                                    st.markdown("---")
                
                st.markdown("---")
        
        # Quick question buttons
        st.markdown("**Quick Questions:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🎯 Best Entry Strategies", key="q1"):
                selected_question = "What are the best entry strategies for mean reversion trades?"
                st.session_state.selected_question = selected_question
                st.rerun()
        
        with col2:
            if st.button("⚠️ Risk Management", key="q2"):
                selected_question = "What are the key risk management principles I should follow?"
                st.session_state.selected_question = selected_question
                st.rerun()
        
        with col3:
            if st.button("📊 Market Context", key="q3"):
                selected_question = "How should I analyze market context before entering trades?"
                st.session_state.selected_question = selected_question
                st.rerun()
        
        # Chat input
        if "selected_question" in st.session_state:
            default_question = st.session_state.selected_question
            del st.session_state.selected_question
        else:
            default_question = ""
        
        spicy_question = st.text_input(
            "What do you want to ask Spicy?",
            value=default_question,
            key="spicy_question"
        )
        
        # Send button
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔥 Ask Spicy", type="primary"):
                if not spicy_question.strip():
                    st.warning("Please type a question before sending.")
                else:
                    try:
                        with st.spinner("🔥 Spicy is thinking..."):
                            excerpts = query_store(spicy_question, k=3)
                        
                        if excerpts:
                            answer = f"Great question! Based on your lessons, here's what I know:\n\n"
                            for i, excerpt in enumerate(excerpts, 1):
                                clean_excerpt = excerpt.replace('\n', ' ').strip()
                                answer += f"**{i}.** {clean_excerpt[:250]}...\n\n"
                            answer += "\n🔥 **Spicy's Take:** Remember, context is everything. Always check market conditions before applying these strategies!"
                            
                            st.session_state.chat_history.append((spicy_question, answer, excerpts))
                            st.success("✅ Spicy responded!")
                            st.rerun()
                        else:
                            st.info("🤔 Spicy doesn't have enough knowledge about that yet. Try uploading more lessons or rephrasing your question.")
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        with col2:
            if st.button("🗑️ Clear Chat", type="secondary"):
                st.session_state.chat_history = []
                st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        **About JumpTrader:**
        - Real-time Binance perpetual futures data
        - WebSocket-powered live trade ticks
        - Orion Terminal CLI integration
        - AI-powered signal detection
        - Volume spike alerts
        - Momentum pattern recognition
        - Range break detection
        - Micro-spike detection from real-time ticks
        - Funding rate and open interest tracking
        - **🔥 AI Mentor Chat Agent trained on trading lessons**
        """
    )

if __name__ == "__main__":
    main() 