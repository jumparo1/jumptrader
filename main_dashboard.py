import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    return ", ".join(signals) if signals else "-"

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
        min_value=10,
        max_value=min(500, len(symbols)),
        value=100,
        step=10
    )
    
    # Auto-refresh control
    st.sidebar.header("🔄 Auto-Refresh")
    refresh_interval = st.sidebar.number_input(
        "Refresh interval (seconds)",
        min_value=10,
        value=60,
        step=5
    )
    
    # Status indicators
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🔗 Connection", "✅ Connected")
    
    with col2:
        st.metric("📊 Symbols Available", len(symbols))
    
    with col3:
        st.metric("🕒 Last Update", datetime.now().strftime("%H:%M:%S"))
    
    with col4:
        st.metric("⚡ Refresh Rate", f"{refresh_interval}s")
    
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
            
            # Combine data
            row_data = {
                **ticker_data,
                "change_1h": change_1h
            }
            
            # Compute signals
            row_data["signals"] = compute_signals(row_data)
            
            market_data.append(row_data)
        
        # Small delay to avoid rate limiting
        time.sleep(0.01)
    
    progress_bar.progress(1.0)
    status_text.text("Data loaded successfully!")
    
    if market_data:
        # Convert to DataFrame
        df = pd.DataFrame(market_data)
        
        # Sort by 24h change
        df = df.sort_values("priceChangePercent", ascending=False)
        
        # Format display columns
        display_df = df[[
            "symbol", "lastPrice", "change_1h", "priceChangePercent", 
            "quoteVolume", "highPrice", "lowPrice", "signals"
        ]].copy()
        
        # Format numbers
        display_df["lastPrice"] = display_df["lastPrice"].round(4)
        display_df["change_1h"] = display_df["change_1h"].round(2)
        display_df["priceChangePercent"] = display_df["priceChangePercent"].round(2)
        display_df["quoteVolume"] = (display_df["quoteVolume"] / 1_000_000).round(1)  # Convert to millions
        
        # Rename columns for display
        display_df.columns = [
            "Symbol", "Price", "1H %", "24H %", "Volume (M)", "High", "Low", "Signals"
        ]
        
        # Display the data
        st.dataframe(
            display_df,
            use_container_width=True,
            height=600
        )
        
        # Summary statistics
        st.subheader("📊 Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
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
        
    else:
        st.warning("No market data available. Please check your connection.")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        **About JumpTrader:**
        - Real-time Binance perpetual futures data
        - AI-powered signal detection
        - Volume spike alerts
        - Momentum pattern recognition
        - Range break detection
        """
    )

if __name__ == "__main__":
    main() 