#!/usr/bin/env python3
"""
Test script to verify all JumpTrader components work correctly.
"""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.market_data_manager import MarketDataManager
from signals.signal_processor import SignalProcessor
from clients.binance_client import BinanceDataClient
from config.settings import DEFAULT_SYMBOLS_LIMIT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_binance_client():
    """Test Binance client functionality."""
    print("🔍 Testing Binance Client...")
    
    client = BinanceDataClient()
    
    # Test getting symbols
    symbols = client.get_perpetual_symbols()
    print(f"✅ Found {len(symbols)} perpetual symbols")
    
    if symbols:
        # Test getting market data for first few symbols
        test_symbols = symbols[:5]
        print(f"📊 Testing market data for: {test_symbols}")
        
        for symbol in test_symbols:
            ticker = client.get_24h_ticker(symbol)
            if ticker:
                print(f"  ✅ {symbol}: ${ticker['last_price']:.4f} ({ticker['price_change_percent']:+.2f}%)")
            else:
                print(f"  ❌ {symbol}: Failed to get ticker")
    
    return True

async def test_signal_processor():
    """Test signal processor functionality."""
    print("\n🔍 Testing Signal Processor...")
    
    processor = SignalProcessor()
    
    # Create sample market data
    sample_data = {
        "BTCUSDT": {
            "last_price": 50000.0,
            "price_change_percent": 5.2,
            "quote_volume": 1000000000.0,
            "open_interest": {"open_interest": 5000000.0},
            "funding_rate": {"funding_rate": 0.0001}
        },
        "ETHUSDT": {
            "last_price": 3000.0,
            "price_change_percent": -2.1,
            "quote_volume": 500000000.0,
            "open_interest": {"open_interest": 2000000.0},
            "funding_rate": {"funding_rate": -0.0002}
        }
    }
    
    # Process signals
    signals = processor.process_market_data(sample_data)
    print(f"✅ Generated signals for {len(signals)} symbols")
    
    for symbol, symbol_signals in signals.items():
        if symbol_signals:
            print(f"  📈 {symbol}: {', '.join(symbol_signals)}")
        else:
            print(f"  ⚪ {symbol}: No signals")
    
    return True

async def test_data_manager():
    """Test data manager functionality."""
    print("\n🔍 Testing Data Manager...")
    
    manager = MarketDataManager()
    
    # Test getting symbols
    symbols = manager.get_perpetual_symbols()
    print(f"✅ Data manager found {len(symbols)} symbols")
    
    if symbols:
        # Test fetching market data for a few symbols
        test_symbols = symbols[:3]
        print(f"📊 Fetching market data for: {test_symbols}")
        
        market_data = await manager.fetch_market_data(test_symbols)
        print(f"✅ Fetched market data for {len(market_data)} symbols")
        
        # Test signal processing
        processor = SignalProcessor()
        signals = processor.process_market_data(market_data)
        print(f"✅ Generated signals for {len(signals)} symbols")
        
        # Show some results
        for symbol in test_symbols:
            if symbol in market_data:
                data = market_data[symbol]
                symbol_signals = signals.get(symbol, [])
                print(f"  📈 {symbol}: ${data['last_price']:.4f} ({data['price_change_percent']:+.2f}%) - {len(symbol_signals)} signals")
    
    return True

async def test_configuration():
    """Test configuration loading."""
    print("\n🔍 Testing Configuration...")
    
    from config.settings import (
        BINANCE_API_KEY, BINANCE_API_SECRET, CANDLE_INTERVALS,
        VOLUME_SPIKE_THRESHOLD, PRICE_CHANGE_THRESHOLDS
    )
    
    print(f"✅ Configuration loaded successfully")
    print(f"  📊 Binance API Key: {'✅ Set' if BINANCE_API_KEY else '❌ Not set'}")
    print(f"  📊 Binance API Secret: {'✅ Set' if BINANCE_API_SECRET else '❌ Not set'}")
    print(f"  📊 Candle Intervals: {len(CANDLE_INTERVALS)} configured")
    print(f"  📊 Volume Spike Threshold: {VOLUME_SPIKE_THRESHOLD}x")
    print(f"  📊 Price Change Thresholds: {len(PRICE_CHANGE_THRESHOLDS)} timeframes")
    
    return True

async def main():
    """Run all tests."""
    print("🚀 JumpTrader Component Tests")
    print("=" * 50)
    
    try:
        # Test configuration
        await test_configuration()
        
        # Test Binance client
        await test_binance_client()
        
        # Test signal processor
        await test_signal_processor()
        
        # Test data manager
        await test_data_manager()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        print("\n🎉 JumpTrader is ready to use!")
        print("Run the dashboard with: streamlit run main_dashboard.py")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error(f"Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(main()) 