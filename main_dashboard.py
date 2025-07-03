import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import logging
import asyncio
import threading
from clients.ws_client import WebSocketClient
from clients.orion_cli import fetch_orion_data, test_orion_cli
from clients.binance import get_btc_correlation

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
            # Focus on top 10 symbols for faster loading
            ws_symbols = symbols[:10]  # top 10 symbols only
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

def main():
    # Header
    st.title("🚀 JumpTrader - AI Trading Dashboard")
    st.markdown("Real-time Binance Perpetuals with AI-Powered Signals")
    st.info("⚡ **Optimized Mode**: Loading top 10 perpetual contracts for faster performance")
    
    # Sidebar controls
    st.sidebar.header("⚙️ Dashboard Controls")
    
    # Get symbols
    symbols = get_perpetual_symbols()
    if not symbols:
        st.error("Failed to fetch symbols from Binance")
        return
    
    # Start WebSocket client for real-time ticks
    start_websocket_client(symbols)
    
    # Consume any available ticks
    consume_ticks()
    
    # Test and fetch Orion CLI data
    orion_available = test_orion_cli()
    # Symbol limit control - optimized for top 10
    symbol_limit = st.sidebar.slider(
        "Number of symbols to display",
        min_value=5,
        max_value=min(50, len(symbols)),
        value=10,
        step=5
    )
    symbols_to_fetch = symbols[:symbol_limit]
    if orion_available:
        orion_data = get_orion_snapshot(symbols_to_fetch)
        st.session_state.orion_data = orion_data
        logger.info(f"Orion CLI data loaded: {len(orion_data)} symbols")
        # Optionally, show a warning if any symbols are missing (all will be present, but some may be all-zero)
        missing = [s for s, v in orion_data.items() if v["tickCount"] == 0 and v["fundingRate"] == 0.0 and v["openInterest"] == 0.0]
        if missing:
            st.warning(f"Orion CLI returned no data for: {missing}")
            logger.warning(f"Orion CLI returned no data for: {missing}")
    else:
        st.session_state.orion_data = {}
        logger.warning("Orion CLI not available")
    
    # Auto-refresh control
    st.sidebar.header("🔄 Auto-Refresh")
    refresh_interval = st.sidebar.number_input(
        "Refresh interval (seconds)",
        min_value=10,
        value=60,
        step=5
    )
    
    # Status indicators
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("🔗 Connection", "✅ Connected")
    
    with col2:
        st.metric("📊 Symbols Available", f"{symbol_limit}/{len(symbols)}")
    
    with col3:
        st.metric("🕒 Last Update", datetime.now().strftime("%H:%M:%S"))
    
    with col4:
        st.metric("⚡ Refresh Rate", f"{refresh_interval}s")
        
    with col5:
        ws_status = "🟢 Active" if st.session_state.ws_started else "🔴 Inactive"
        tick_count = len(st.session_state.ticks)
        st.metric("📡 WebSocket", f"{ws_status} ({tick_count} ticks)")
        
    # Add Orion CLI status
    col6, col7 = st.columns(2)
    with col6:
        orion_status = "🟢 Active" if st.session_state.get('orion_data', {}) else "🔴 Inactive"
        orion_count = len(st.session_state.get('orion_data', {}))
        st.metric("🔧 Orion CLI", f"{orion_status} ({orion_count} symbols)")
    
    # Main data section
    st.header("📈 Market Data")
    
    # Progress bar for data fetching
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Fetch data for selected symbols
    status_text.text("Fetching market data...")
    
    market_data = []
    symbols_to_fetch = symbols[:symbol_limit]
    
    for i, symbol in enumerate(symbols_to_fetch):
        # Update progress
        progress = (i + 1) / len(symbols_to_fetch)
        progress_bar.progress(progress)
        status_text.text(f"Fetching data for {symbol}... ({i+1}/{len(symbols_to_fetch)})")
        
        # Get ticker data
        ticker_data = get_24h_ticker_data(symbol)
        if ticker_data:
            # Get 1h change
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
            btc_corr = get_btc_correlation(symbol)
            
            # Combine data
            row_data = {
                **ticker_data,
                "change_1h": change_1h,
                "btc_corr": btc_corr,
                "last_tick_price": last_tick_price,
                "tick_volume": tick_volume,
                "tickCount": tick_count,
                "fundingRate": funding_rate,
                "openInterest": open_interest
            }
            
            # Compute signals
            row_data["signals"] = compute_signals(row_data)
            
            market_data.append(row_data)
        
        # Minimal delay for faster loading with fewer symbols
        time.sleep(0.005)
    
    progress_bar.progress(1.0)
    status_text.text("Data loaded successfully!")
    
    if market_data:
        # Convert to DataFrame
        df = pd.DataFrame(market_data)
        
        # Sort by 24h change
        df = df.sort_values("priceChangePercent", ascending=False)
        
        # Format display columns
        display_df = df[[
            "symbol", "lastPrice", "change_1h", "btc_corr", "priceChangePercent", 
            "quoteVolume", "tickCount", "fundingRate", "openInterest", "signals"
        ]].copy()
        
        # Format numbers
        display_df["lastPrice"] = display_df["lastPrice"].round(4)
        display_df["change_1h"] = display_df["change_1h"].round(2)
        display_df["btc_corr"] = display_df["btc_corr"].round(2)
        display_df["priceChangePercent"] = display_df["priceChangePercent"].round(2)
        display_df["quoteVolume"] = (display_df["quoteVolume"] / 1_000_000).round(1)  # Convert to millions
        
        # Format Orion data
        display_df["tickCount"] = display_df["tickCount"].astype(int)
        display_df["fundingRate"] = (display_df["fundingRate"] * 100).round(4)  # Convert to percentage
        display_df["openInterest"] = (display_df["openInterest"] / 1_000_000).round(1)  # Convert to millions
        
        # Rename columns for display
        display_df.columns = [
            "Symbol", "Price", "1H %", "BTC Corr", "24H %", "Volume (M)", 
            "Tick Count", "Funding %", "OI (M)", "Signals"
        ]
        
        # Style: color 1H %
        styled = display_df.style.applymap(
            lambda v: "color: green;" if v > 0 else "color: red;",
            subset=["1H %"]
        ).format({
            "BTC Corr": "{:.2f}"
        })
        
        # Display the data
        st.dataframe(
            styled,
            use_container_width=True,
            height=600
        )
        
        # Summary statistics
        st.subheader("📊 Summary Statistics")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            gainers = len(df[df["priceChangePercent"] > 0])
            st.metric("📈 Gainers", gainers)
        
        with col2:
            losers = len(df[df["priceChangePercent"] < 0])
            st.metric("📉 Losers", losers)
        
        with col3:
            avg_volume = df["quoteVolume"].mean() / 1_000_000
            st.metric("💰 Avg Volume (M)", f"{avg_volume:.1f}")
        
        with col4:
            volatile = len(df[abs(df["priceChangePercent"]) > 10])
            st.metric("⚠️ High Volatility", volatile)
            
        with col5:
            tick_spikes = len(df[df["signals"].str.contains("⚡ Tick Spike", na=False)])
            st.metric("⚡ Tick Spikes", tick_spikes)
            
        # Add Orion-specific metrics
        col6, col7, col8 = st.columns(3)
        with col6:
            avg_funding = df["fundingRate"].mean() * 100
            st.metric("💰 Avg Funding %", f"{avg_funding:.4f}")
        
        with col7:
            total_oi = df["openInterest"].sum() / 1_000_000
            st.metric("📊 Total OI (M)", f"{total_oi:.1f}")
        
        with col8:
            total_ticks = df["tickCount"].sum()
            st.metric("🔢 Total Ticks", f"{total_ticks:,}")
        
    else:
        st.warning("No market data available. Please check your connection.")
    
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
        """
    )

if __name__ == "__main__":
    main() 