import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np

def create_header():
    """Create the main dashboard header."""
    st.set_page_config(
        page_title="JumpTrader - AI Trading Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🚀 JumpTrader - AI Trading Dashboard")
        st.markdown("**Real-time Binance Perpetuals with AI-Powered Signals**")
    
    # Add timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def create_sidebar_controls():
    """Create sidebar controls for dashboard configuration."""
    st.sidebar.header("⚙️ Dashboard Controls")
    
    # Symbol selection
    st.sidebar.subheader("Symbol Selection")
    symbol_limit = st.sidebar.slider(
        "Number of symbols to display",
        min_value=10,
        max_value=500,
        value=100,
        step=10,
        help="Select how many symbols to load and display"
    )
    
    # Auto-refresh settings
    st.sidebar.subheader("🔄 Auto-Refresh")
    auto_refresh = st.sidebar.checkbox("Enable auto-refresh", value=True)
    refresh_interval = st.sidebar.number_input(
        "Refresh interval (seconds)",
        min_value=30,
        max_value=300,
        value=60,
        step=10,
        disabled=not auto_refresh
    )
    
    # Signal filters
    st.sidebar.subheader("🎯 Signal Filters")
    show_volume_signals = st.sidebar.checkbox("Volume Spikes", value=True)
    show_momentum_signals = st.sidebar.checkbox("Momentum Patterns", value=True)
    show_breakout_signals = st.sidebar.checkbox("Range Breaks", value=True)
    show_price_signals = st.sidebar.checkbox("Price Movements", value=True)
    
    # Sort options
    st.sidebar.subheader("📊 Sort Options")
    sort_by = st.sidebar.selectbox(
        "Sort by",
        options=[
            "24h Change %",
            "1h Change %",
            "Volume",
            "Signal Count",
            "Symbol"
        ],
        index=0
    )
    
    sort_order = st.sidebar.selectbox(
        "Sort order",
        options=["Descending", "Ascending"],
        index=0
    )
    
    return {
        "symbol_limit": symbol_limit,
        "auto_refresh": auto_refresh,
        "refresh_interval": refresh_interval,
        "signal_filters": {
            "volume": show_volume_signals,
            "momentum": show_momentum_signals,
            "breakout": show_breakout_signals,
            "price": show_price_signals
        },
        "sort_by": sort_by,
        "sort_order": sort_order
    }

def create_status_indicators(data_manager, signal_processor):
    """Create status indicators showing data freshness and signal counts."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Data freshness indicator
        market_data_age = data_manager.get_data_age('market_data')
        if market_data_age:
            if market_data_age.total_seconds() < 60:
                st.success(f"🟢 Market Data: {market_data_age.total_seconds():.0f}s ago")
            elif market_data_age.total_seconds() < 300:
                st.warning(f"🟡 Market Data: {market_data_age.total_seconds():.0f}s ago")
            else:
                st.error(f"🔴 Market Data: {market_data_age.total_seconds():.0f}s ago")
        else:
            st.info("⚪ Market Data: Not available")
    
    with col2:
        # Signal count indicator
        latest_signals = signal_processor.signal_history.get(max(signal_processor.signal_history.keys()), {})
        total_signals = sum(len(signals) for signals in latest_signals.values())
        st.metric("🎯 Active Signals", total_signals)
    
    with col3:
        # WebSocket status
        if data_manager.is_running:
            st.success("🟢 WebSocket: Connected")
        else:
            st.error("🔴 WebSocket: Disconnected")
    
    with col4:
        # Symbol count
        symbol_count = len(data_manager.market_data)
        st.metric("📈 Symbols", symbol_count)

def create_signal_summary(signals: Dict[str, List[str]]):
    """Create a summary of signal types."""
    if not signals:
        st.info("No signals detected yet.")
        return
    
    # Count signal types
    signal_counts = {}
    for symbol_signals in signals.values():
        for signal in symbol_signals:
            if "🔥" in signal:
                signal_counts["Volume Spikes"] = signal_counts.get("Volume Spikes", 0) + 1
            elif "📈" in signal or "📉" in signal:
                signal_counts["Price Moves"] = signal_counts.get("Price Moves", 0) + 1
            elif "🟢" in signal or "🔴" in signal:
                signal_counts["Momentum"] = signal_counts.get("Momentum", 0) + 1
            elif "🚀" in signal or "💥" in signal:
                signal_counts["Breakouts"] = signal_counts.get("Breakouts", 0) + 1
            elif "📊" in signal or "⚡" in signal:
                signal_counts["Acceleration"] = signal_counts.get("Acceleration", 0) + 1
            elif "📐" in signal or "📏" in signal:
                signal_counts["Consolidation"] = signal_counts.get("Consolidation", 0) + 1
    
    if signal_counts:
        st.subheader("📊 Signal Summary")
        
        # Create columns for signal types
        cols = st.columns(len(signal_counts))
        for i, (signal_type, count) in enumerate(signal_counts.items()):
            with cols[i]:
                st.metric(signal_type, count)

def create_main_data_table(market_data: Dict[str, Dict], signals: Dict[str, List[str]], controls: Dict):
    """Create the main data table with market data and signals."""
    if not market_data:
        st.info("No market data available. Please wait for data to load...")
        return
    
    # Convert to DataFrame
    rows = []
    for symbol, data in market_data.items():
        row = {
            "Symbol": symbol,
            "Last Price": data.get("last_price", 0),
            "24h Change %": data.get("price_change_percent", 0),
            "1h Change %": data.get("price_change_percent", 0),  # Will be calculated from klines
            "Volume": data.get("quote_volume", 0),
            "Open Interest": data.get("open_interest", {}).get("open_interest", 0) if data.get("open_interest") else 0,
            "Funding Rate": data.get("funding_rate", {}).get("funding_rate", 0) if data.get("funding_rate") else 0,
            "Signals": ", ".join(signals.get(symbol, []))
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    if df.empty:
        st.info("No data to display")
        return
    
    # Apply filters
    filtered_df = df.copy()
    
    # Apply signal filters
    if not all(controls["signal_filters"].values()):
        mask = pd.Series([False] * len(filtered_df))
        for i, row in filtered_df.iterrows():
            signals_str = row["Signals"]
            has_valid_signal = False
            
            if controls["signal_filters"]["volume"] and "🔥" in signals_str:
                has_valid_signal = True
            if controls["signal_filters"]["momentum"] and ("🟢" in signals_str or "🔴" in signals_str):
                has_valid_signal = True
            if controls["signal_filters"]["breakout"] and ("🚀" in signals_str or "💥" in signals_str):
                has_valid_signal = True
            if controls["signal_filters"]["price"] and ("📈" in signals_str or "📉" in signals_str):
                has_valid_signal = True
            
            mask[i] = has_valid_signal
        
        filtered_df = filtered_df[mask]
    
    # Apply sorting
    sort_column_map = {
        "24h Change %": "24h Change %",
        "1h Change %": "1h Change %",
        "Volume": "Volume",
        "Signal Count": "Signals",
        "Symbol": "Symbol"
    }
    
    sort_column = sort_column_map.get(controls["sort_by"], "24h Change %")
    ascending = controls["sort_order"] == "Ascending"
    
    if sort_column == "Signals":
        # Sort by number of signals
        filtered_df["Signal Count"] = filtered_df["Signals"].apply(lambda x: len(x.split(", ")) if x else 0)
        filtered_df = filtered_df.sort_values("Signal Count", ascending=ascending)
    else:
        filtered_df = filtered_df.sort_values(sort_column, ascending=ascending)
    
    # Format the DataFrame for display
    display_df = filtered_df.copy()
    
    # Format numeric columns
    display_df["Last Price"] = display_df["Last Price"].apply(lambda x: f"${x:,.4f}" if x else "-")
    display_df["24h Change %"] = display_df["24h Change %"].apply(lambda x: f"{x:+.2f}%" if x else "-")
    display_df["1h Change %"] = display_df["1h Change %"].apply(lambda x: f"{x:+.2f}%" if x else "-")
    display_df["Volume"] = display_df["Volume"].apply(lambda x: f"${x:,.0f}" if x else "-")
    display_df["Open Interest"] = display_df["Open Interest"].apply(lambda x: f"{x:,.0f}" if x else "-")
    display_df["Funding Rate"] = display_df["Funding Rate"].apply(lambda x: f"{x:.4f}%" if x else "-")
    
    # Display the table
    st.subheader("📈 Market Data & Signals")
    
    # Add search/filter
    search_term = st.text_input("🔍 Search symbols:", placeholder="e.g., BTC, ETH")
    if search_term:
        display_df = display_df[display_df["Symbol"].str.contains(search_term.upper(), na=False)]
    
    # Display the table with custom styling
    st.dataframe(
        display_df,
        use_container_width=True,
        height=600,
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol", width="medium"),
            "Last Price": st.column_config.TextColumn("Last Price", width="medium"),
            "24h Change %": st.column_config.TextColumn("24h Change %", width="medium"),
            "1h Change %": st.column_config.TextColumn("1h Change %", width="medium"),
            "Volume": st.column_config.TextColumn("Volume", width="medium"),
            "Open Interest": st.column_config.TextColumn("OI", width="small"),
            "Funding Rate": st.column_config.TextColumn("Funding", width="small"),
            "Signals": st.column_config.TextColumn("Signals", width="large")
        }
    )
    
    st.caption(f"Showing {len(display_df)} of {len(df)} symbols")

def create_mini_chart(symbol: str, klines_data: List[Dict], height: int = 200):
    """Create a mini candlestick chart for a symbol."""
    if not klines_data or len(klines_data) < 2:
        return None
    
    # Prepare data for plotting
    df = pd.DataFrame(klines_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Create candlestick chart
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=symbol
    )])
    
    fig.update_layout(
        title=f"{symbol} Price Chart",
        xaxis_title="Time",
        yaxis_title="Price",
        height=height,
        showlegend=False,
        margin=dict(l=10, r=10, t=30, b=10)
    )
    
    return fig

def create_signal_alert(symbol: str, signals: List[str]):
    """Create an alert component for new signals."""
    if not signals:
        return
    
    st.warning(f"🚨 New signals for {symbol}:")
    for signal in signals:
        st.write(f"  • {signal}")

def create_performance_metrics(market_data: Dict[str, Dict]):
    """Create performance metrics dashboard."""
    if not market_data:
        return
    
    st.subheader("📊 Performance Metrics")
    
    # Calculate metrics
    total_volume = sum(data.get("quote_volume", 0) for data in market_data.values())
    avg_change_24h = np.mean([data.get("price_change_percent", 0) for data in market_data.values()])
    
    # Count gainers vs losers
    gainers = sum(1 for data in market_data.values() if data.get("price_change_percent", 0) > 0)
    losers = sum(1 for data in market_data.values() if data.get("price_change_percent", 0) < 0)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Volume", f"${total_volume:,.0f}")
    
    with col2:
        st.metric("Avg 24h Change", f"{avg_change_24h:+.2f}%")
    
    with col3:
        st.metric("Gainers", gainers)
    
    with col4:
        st.metric("Losers", losers) 