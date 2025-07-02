import asyncio
import logging
import streamlit as st
import time
from datetime import datetime
import sys
import os
import threading

# Ensure there's an event loop for Streamlit's thread
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.market_data_manager import MarketDataManager
from signals.signal_processor import SignalProcessor
from ui.dashboard_components import (
    create_header, create_sidebar_controls, create_status_indicators,
    create_signal_summary, create_main_data_table, create_performance_metrics
)
from config.settings import DEFAULT_SYMBOLS_LIMIT, AUTO_REFRESH_INTERVAL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize session state
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = None
if 'signal_processor' not in st.session_state:
    st.session_state.signal_processor = None
if 'is_initialized' not in st.session_state:
    st.session_state.is_initialized = False
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None

def initialize_components():
    """Initialize data manager and signal processor."""
    if not st.session_state.is_initialized:
        try:
            st.session_state.data_manager = MarketDataManager()
            st.session_state.signal_processor = SignalProcessor()
            st.session_state.is_initialized = True
            logger.info("Components initialized successfully")
        except Exception as e:
            st.error(f"Error initializing components: {e}")
            logger.error(f"Error initializing components: {e}")

def data_callback(data_type: str, data: dict):
    """Callback function for data updates."""
    try:
        if data_type == 'market_data':
            # Process signals when new market data arrives
            signals = st.session_state.signal_processor.process_market_data(
                data, 
                st.session_state.data_manager.klines_data
            )
            st.session_state.current_signals = signals
            logger.info(f"Processed signals for {len(signals)} symbols")
    except Exception as e:
        logger.error(f"Error in data callback: {e}")

def main():
    """Main dashboard application."""
    # Create header
    create_header()
    
    # Initialize components
    initialize_components()
    
    if not st.session_state.is_initialized:
        st.error("Failed to initialize dashboard components")
        return
    
    # Get sidebar controls
    controls = create_sidebar_controls()
    
    # Sidebar info
    st.sidebar.markdown("---")
    st.sidebar.subheader("ℹ️ About")
    st.sidebar.markdown("""
    **JumpTrader** is an AI-powered trading dashboard that monitors Binance perpetual futures.
    
    **Features:**
    - Real-time market data
    - AI signal detection
    - Volume spike alerts
    - Momentum pattern recognition
    - Range break detection
    
    **Data Sources:**
    - Binance Futures API
    - WebSocket streams
    - Orion Protocol (future)
    """)
    
    # Main content area
    try:
        # Get symbols
        symbols = st.session_state.data_manager.get_perpetual_symbols()
        if not symbols:
            st.error("Failed to fetch perpetual symbols from Binance")
            return
        
        # Limit symbols based on user selection
        symbols = symbols[:controls["symbol_limit"]]
        
        # Start data collection if not already running
        if not st.session_state.data_manager.is_running:
            # Add data callback
            st.session_state.data_manager.add_data_callback(data_callback)
            
            def start_data_collection_thread(symbols):
                st.session_state.data_manager.start_data_collection_sync(symbols)
            thread = threading.Thread(target=start_data_collection_thread, args=(symbols,), daemon=True)
            thread.start()
            st.info(f"Starting data collection for {len(symbols)} symbols...")
        
        # Status indicators
        create_status_indicators(st.session_state.data_manager, st.session_state.signal_processor)
        
        # Performance metrics
        market_data = st.session_state.data_manager.get_latest_data('market_data')
        if market_data:
            create_performance_metrics(market_data)
        
        # Signal summary
        current_signals = getattr(st.session_state, 'current_signals', {})
        if current_signals:
            create_signal_summary(current_signals)
        
        # Main data table
        create_main_data_table(market_data, current_signals, controls)
        
        # Auto-refresh logic
        if controls["auto_refresh"]:
            current_time = datetime.now()
            if (st.session_state.last_refresh is None or 
                (current_time - st.session_state.last_refresh).total_seconds() >= controls["refresh_interval"]):
                
                st.session_state.last_refresh = current_time
                st.rerun()
        
        # Manual refresh button
        if st.button("🔄 Manual Refresh"):
            st.rerun()
        
        # Data age information
        st.sidebar.markdown("---")
        st.sidebar.subheader("📊 Data Status")
        
        market_data_age = st.session_state.data_manager.get_data_age('market_data')
        if market_data_age:
            st.sidebar.metric("Market Data Age", f"{market_data_age.total_seconds():.0f}s")
        
        klines_data_age = st.session_state.data_manager.get_data_age('klines_data')
        if klines_data_age:
            st.sidebar.metric("Klines Data Age", f"{klines_data_age.total_seconds():.0f}s")
        
        # Connection status
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔗 Connection Status")
        
        if st.session_state.data_manager.is_running:
            st.sidebar.success("✅ Data Collection Active")
        else:
            st.sidebar.error("❌ Data Collection Stopped")
        
        if st.session_state.data_manager.binance_client.client:
            st.sidebar.success("✅ Binance API Connected")
        else:
            st.sidebar.warning("⚠️ Binance API (Public Only)")
        
        if st.session_state.data_manager.orion_client:
            st.sidebar.info("ℹ️ Orion Integration Available")
        else:
            st.sidebar.info("ℹ️ Orion Integration Disabled")
        
    except Exception as e:
        st.error(f"Error in main dashboard: {e}")
        logger.error(f"Error in main dashboard: {e}")

if __name__ == "__main__":
    main() 