#!/usr/bin/env python3
"""
Debug script to check Binance API response structure.
"""

import requests
import json

def debug_binance_api():
    """Debug the Binance API response structure."""
    
    # Test the 24h ticker endpoint
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    params = {"symbol": "BTCUSDT"}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        print("🔍 Binance API Response Structure:")
        print("=" * 50)
        print(json.dumps(data, indent=2))
        print("=" * 50)
        
        # Check which fields are actually present
        print("\n📊 Available fields:")
        for key, value in data.items():
            print(f"  {key}: {type(value).__name__} = {value}")
        
        # Test which fields might be missing
        required_fields = [
            "symbol", "priceChange", "priceChangePercent", "weightedAvgPrice",
            "prevClosePrice", "lastPrice", "lastQty", "bidPrice", "askPrice",
            "openPrice", "highPrice", "lowPrice", "volume", "quoteVolume"
        ]
        
        print("\n🔍 Checking required fields:")
        for field in required_fields:
            if field in data:
                print(f"  ✅ {field}: {data[field]}")
            else:
                print(f"  ❌ {field}: MISSING")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_binance_api() 