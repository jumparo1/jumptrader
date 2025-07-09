"""
RSI (Relative Strength Index) calculations for multiple timeframes.

This module implements Wilder's RSI formula and provides functions to:
- Fetch closing prices from Binance
- Calculate RSI for different periods
- Get RSI values across multiple timeframes
"""

from typing import List, Dict
import logging
import sys
import os

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.binance_client import BinanceDataClient

logger = logging.getLogger(__name__)

# Initialize Binance client
binance_client = BinanceDataClient()


def fetch_closes(symbol: str, interval: str, limit: int) -> List[float]:
    """
    Fetch closing prices for a symbol and interval.
    
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        interval: Time interval (e.g., '1h', '15m', '5m', '1m')
        limit: Number of candles to fetch
        
    Returns:
        List of closing prices as floats
    """
    try:
        klines = binance_client.get_klines(symbol, interval, limit)
        closes = [float(candle['close']) for candle in klines]
        logger.debug(f"Fetched {len(closes)} closing prices for {symbol} {interval}")
        return closes
    except Exception as e:
        logger.error(f"Error fetching closes for {symbol} {interval}: {e}")
        return []


def compute_rsi(closes: List[float], period: int = 14) -> float:
    """
    Compute RSI using Wilder's formula.
    
    Args:
        closes: List of closing prices
        period: RSI period (default: 14)
        
    Returns:
        RSI value as float (0-100)
    """
    if len(closes) < period + 1:
        logger.warning(f"Not enough data for RSI calculation. Need at least {period + 1} prices, got {len(closes)}")
        return 50.0  # Return neutral RSI if insufficient data
    
    # Calculate price changes
    changes = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        changes.append(change)
    
    # Separate gains and losses
    gains = [change if change > 0 else 0 for change in changes]
    losses = [-change if change < 0 else 0 for change in changes]
    
    # Calculate initial average gain and loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Apply Wilder's smoothing
    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    # Calculate RSI
    if avg_loss == 0:
        return 100.0  # Avoid division by zero
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 2)


def get_multi_rsi(symbol: str) -> Dict[str, float]:
    """
    Get RSI values for multiple timeframes.
    
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        
    Returns:
        Dictionary with RSI values for different timeframes
    """
    rsi_values = {}
    
    # Define timeframes and their limits
    timeframes = {
        '1h': 168,   # 1 week of hourly data
        '15m': 168,  # 1 week of 15-minute data  
        '5m': 168,   # 1 week of 5-minute data
        '1m': 168    # 1 week of 1-minute data
    }
    
    for interval, limit in timeframes.items():
        try:
            closes = fetch_closes(symbol, interval, limit)
            if closes:
                rsi = compute_rsi(closes)
                rsi_values[f'rsi_{interval}'] = rsi
                logger.debug(f"RSI {interval} for {symbol}: {rsi}")
            else:
                rsi_values[f'rsi_{interval}'] = 50.0  # Neutral RSI if no data
                logger.warning(f"No closing data available for {symbol} {interval}")
        except Exception as e:
            logger.error(f"Error calculating RSI for {symbol} {interval}: {e}")
            rsi_values[f'rsi_{interval}'] = 50.0  # Neutral RSI on error
    
    return rsi_values


if __name__ == "__main__":
    # Test the RSI calculation
    print("Testing RSI calculation for BTCUSDT...")
    rsi_results = get_multi_rsi("BTCUSDT")
    
    for k, v in rsi_results.items():
        print(f"{k}: {v:.2f}")
    
    # Test with sample data
    print("\nTesting RSI with sample data...")
    sample_closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.34, 44.09, 44.15, 43.61, 44.33, 44.34, 44.09, 44.15, 43.61, 44.33]
    sample_rsi = compute_rsi(sample_closes)
    print(f"Sample RSI: {sample_rsi:.2f}") 