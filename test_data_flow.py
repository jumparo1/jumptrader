#!/usr/bin/env python3
"""
Test script to verify data flow in MarketDataManager.
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.market_data_manager import MarketDataManager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_data_flow():
    """Test the complete data flow."""
    print("🔍 Testing data flow...")
    
    # Initialize MarketDataManager
    data_manager = MarketDataManager()
    
    # Get symbols
    symbols = data_manager.get_perpetual_symbols()
    print(f"📊 Found {len(symbols)} perpetual symbols")
    
    if not symbols:
        print("❌ No symbols found!")
        return False
    
    # Test with first 5 symbols
    test_symbols = symbols[:5]
    print(f"🧪 Testing with symbols: {test_symbols}")
    
    # Fetch market data
    print("\n📈 Fetching market data...")
    market_data = await data_manager.fetch_market_data(test_symbols)
    print(f"✅ Fetched market data for {len(market_data)} symbols")
    
    # Check stored data
    stored_data = data_manager.get_latest_data('market_data')
    print(f"💾 Stored data: {len(stored_data)} symbols in memory")
    
    # Show sample data
    if stored_data:
        sample_symbol = list(stored_data.keys())[0]
        sample_data = stored_data[sample_symbol]
        print(f"\n📋 Sample data for {sample_symbol}:")
        print(f"   Last Price: {sample_data.get('last_price', 'N/A')}")
        print(f"   24h Change: {sample_data.get('price_change_percent', 'N/A')}%")
        print(f"   Volume: {sample_data.get('quote_volume', 'N/A')}")
    
    return len(stored_data) > 0

if __name__ == "__main__":
    success = asyncio.run(test_data_flow())
    if success:
        print("\n✅ Data flow test passed!")
    else:
        print("\n❌ Data flow test failed!")
        sys.exit(1) 