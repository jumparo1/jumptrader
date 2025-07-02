#!/usr/bin/env python3
"""
Simple test script to verify Binance API functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from clients.binance_client import BinanceDataClient
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_binance_api():
    """Test basic Binance API functionality."""
    print("🔍 Testing Binance API...")
    
    # Initialize client
    client = BinanceDataClient()
    
    # Test 1: Get perpetual symbols
    print("\n1. Testing perpetual symbols fetch...")
    symbols = client.get_perpetual_symbols()
    print(f"   Found {len(symbols)} perpetual symbols")
    if symbols:
        print(f"   First 5 symbols: {symbols[:5]}")
    else:
        print("   ❌ No symbols found!")
        return False
    
    # Test 2: Get ticker data for first symbol
    print("\n2. Testing ticker data fetch...")
    if symbols:
        test_symbol = symbols[0]
        ticker_data = client.get_24h_ticker(test_symbol)
        if ticker_data:
            print(f"   ✅ Successfully fetched ticker data for {test_symbol}")
            print(f"   Last price: {ticker_data.get('last_price', 'N/A')}")
            print(f"   24h change: {ticker_data.get('price_change_percent', 'N/A')}%")
        else:
            print(f"   ❌ Failed to fetch ticker data for {test_symbol}")
            return False
    
    # Test 3: Get klines data
    print("\n3. Testing klines data fetch...")
    if symbols:
        klines_data = client.get_klines(test_symbol, '1h', 10)
        if klines_data:
            print(f"   ✅ Successfully fetched klines data for {test_symbol}")
            print(f"   Number of klines: {len(klines_data)}")
        else:
            print(f"   ❌ Failed to fetch klines data for {test_symbol}")
            return False
    
    print("\n✅ All tests passed!")
    return True

if __name__ == "__main__":
    success = test_binance_api()
    if not success:
        sys.exit(1) 