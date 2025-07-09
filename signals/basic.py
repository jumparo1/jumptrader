"""
Basic signal detection functions for trading analysis.

This module contains functions to detect various market signals:
- Volume spikes
- Open interest jumps  
- Funding rate anomalies
- Price momentum signals
- Volatility signals
"""

from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def detect_volume_spike(current_volume: float, avg_volume: float, threshold: float = 2.0) -> bool:
    """
    Detect if current volume is significantly higher than average volume.
    
    Args:
        current_volume: Current period volume
        avg_volume: Average volume over a reference period
        threshold: Multiplier threshold (default: 2.0 = 200% of average)
        
    Returns:
        True if volume spike detected, False otherwise
    """
    if avg_volume <= 0 or current_volume <= 0:
        return False
    
    ratio = current_volume / avg_volume
    return ratio >= threshold


def detect_oi_jump(current_oi: float, prev_oi: float, threshold: float = 1.5) -> bool:
    """
    Detect if open interest has jumped significantly.
    
    Args:
        current_oi: Current open interest
        prev_oi: Previous open interest
        threshold: Multiplier threshold (default: 1.5 = 150% of previous)
        
    Returns:
        True if OI jump detected, False otherwise
    """
    if prev_oi <= 0 or current_oi <= 0:
        return False
    
    ratio = current_oi / prev_oi
    return ratio >= threshold


def detect_funding_anomaly(funding_rate: float, threshold: float = 0.05) -> bool:
    """
    Detect if funding rate is anomalously high or low.
    
    Args:
        funding_rate: Current funding rate (as decimal, e.g., 0.05 = 5%)
        threshold: Absolute threshold for anomaly detection (default: 0.05 = 5%)
        
    Returns:
        True if funding anomaly detected, False otherwise
    """
    return abs(funding_rate) > threshold


def detect_price_momentum(change_1h: float, threshold: float = 3.0) -> Tuple[bool, str]:
    """
    Detect price momentum based on 1-hour change.
    
    Args:
        change_1h: 1-hour price change percentage
        threshold: Threshold for momentum detection (default: 3.0%)
        
    Returns:
        Tuple of (detected, direction) where direction is 'bullish', 'bearish', or 'neutral'
    """
    if change_1h > threshold:
        return True, "bullish"
    elif change_1h < -threshold:
        return True, "bearish"
    else:
        return False, "neutral"


def detect_volatility(price_change_24h: float, threshold: float = 10.0) -> bool:
    """
    Detect high volatility based on 24-hour price change.
    
    Args:
        price_change_24h: 24-hour price change percentage
        threshold: Threshold for volatility detection (default: 10.0%)
        
    Returns:
        True if high volatility detected, False otherwise
    """
    return abs(price_change_24h) > threshold


def detect_tick_spike(current_price: float, last_price: float, threshold: float = 0.5) -> bool:
    """
    Detect price spikes from real-time tick data.
    
    Args:
        current_price: Current tick price
        last_price: Previous tick price
        threshold: Percentage change threshold (default: 0.5%)
        
    Returns:
        True if tick spike detected, False otherwise
    """
    if last_price <= 0 or current_price <= 0:
        return False
    
    change_percent = abs((current_price - last_price) / last_price) * 100
    return change_percent > threshold


def detect_near_extremes(current_price: float, high_price: float, low_price: float, 
                        threshold: float = 0.01) -> Tuple[bool, str]:
    """
    Detect if price is near daily high or low.
    
    Args:
        current_price: Current price
        high_price: Daily high price
        low_price: Daily low price
        threshold: Distance threshold as fraction (default: 0.01 = 1%)
        
    Returns:
        Tuple of (detected, position) where position is 'near_high', 'near_low', or 'middle'
    """
    if high_price <= 0 or low_price <= 0 or current_price <= 0:
        return False, "middle"
    
    high_distance = (high_price - current_price) / high_price
    low_distance = (current_price - low_price) / low_price
    
    if high_distance <= threshold:
        return True, "near_high"
    elif low_distance <= threshold:
        return True, "near_low"
    else:
        return False, "middle"


def compute_basic_signals(chg1h: float, chg24h: float, vol24h: float) -> list:
    """
    Compute basic trading signals based on 1h change, 24h change, and 24h volume.
    
    Args:
        chg1h: 1-hour price change percentage
        chg24h: 24-hour price change percentage  
        vol24h: 24-hour volume
        
    Returns:
        List of signal tag strings
    """
    signals = []
    
    # Volume spike detection (1B volume threshold)
    if vol24h >= 1e9:
        signals.append("🔥 Volume Spike")
    
    # 1H Gainer detection (5% threshold)
    if chg1h > 5:
        signals.append("📈 1H Gainer")
    
    # Volatile detection (10% 24h change threshold)
    if abs(chg24h) > 10:
        signals.append("⚠️ Volatile")
    
    return signals


def compute_comprehensive_signals(row_data: Dict) -> Dict[str, any]:
    """
    Compute all basic signals for a given row of market data.
    
    Args:
        row_data: Dictionary containing market data with keys:
            - quoteVolume: Current volume
            - openInterest: Current open interest
            - fundingRate: Current funding rate
            - change_1h: 1-hour price change
            - priceChangePercent: 24-hour price change
            - lastPrice: Current price
            - highPrice: Daily high
            - lowPrice: Daily low
            - last_tick_price: Real-time tick price
            
    Returns:
        Dictionary containing all detected signals with their details
    """
    signals = []
    signal_details = {}
    
    # Volume spike detection (using a simple threshold for now)
    # In a real implementation, you'd compare against historical average
    if row_data.get("quoteVolume", 0) > 500_000_000:  # 500M volume threshold
        signals.append("🔥 Volume Spike")
        signal_details["volume_spike"] = {
            "detected": True,
            "volume": row_data.get("quoteVolume", 0),
            "threshold": 500_000_000
        }
    
    # Open interest jump detection
    current_oi = row_data.get("openInterest", 0)
    if current_oi > 0:
        # For now, we'll use a simple threshold
        # In production, you'd compare against previous OI
        if current_oi > 100_000_000:  # 100M OI threshold
            signals.append("💥 OI Jump")
            signal_details["oi_jump"] = {
                "detected": True,
                "current_oi": current_oi,
                "threshold": 100_000_000
            }
    
    # Funding rate anomaly detection
    funding_rate = row_data.get("fundingRate", 0)
    if detect_funding_anomaly(funding_rate, threshold=0.05):
        signals.append("💸 Funding Anomaly")
        signal_details["funding_anomaly"] = {
            "detected": True,
            "funding_rate": funding_rate,
            "threshold": 0.05
        }
    
    # Price momentum detection
    change_1h = row_data.get("change_1h", 0)
    momentum_detected, direction = detect_price_momentum(change_1h, threshold=3.0)
    if momentum_detected:
        if direction == "bullish":
            signals.append("📈 1H Bullish")
        else:
            signals.append("📉 1H Bearish")
        signal_details["price_momentum"] = {
            "detected": True,
            "direction": direction,
            "change_1h": change_1h,
            "threshold": 3.0
        }
    
    # Volatility detection
    price_change_24h = row_data.get("priceChangePercent", 0)
    if detect_volatility(price_change_24h, threshold=10.0):
        signals.append("⚠️ High Volatility")
        signal_details["volatility"] = {
            "detected": True,
            "change_24h": price_change_24h,
            "threshold": 10.0
        }
    
    # Tick spike detection
    current_price = row_data.get("lastPrice", 0)
    last_tick_price = row_data.get("last_tick_price", 0)
    if current_price > 0 and last_tick_price > 0:
        if detect_tick_spike(current_price, last_tick_price, threshold=0.5):
            signals.append("⚡ Tick Spike")
            signal_details["tick_spike"] = {
                "detected": True,
                "current_price": current_price,
                "last_tick_price": last_tick_price,
                "threshold": 0.5
            }
    
    # Near extremes detection
    high_price = row_data.get("highPrice", 0)
    low_price = row_data.get("lowPrice", 0)
    if current_price > 0 and high_price > 0 and low_price > 0:
        near_extreme, position = detect_near_extremes(current_price, high_price, low_price)
        if near_extreme:
            if position == "near_high":
                signals.append("🚀 Near High")
            else:
                signals.append("📉 Near Low")
            signal_details["near_extremes"] = {
                "detected": True,
                "position": position,
                "current_price": current_price,
                "high_price": high_price,
                "low_price": low_price
            }
    
    return {
        "signals": signals,
        "signal_string": ", ".join(signals) if signals else "-",
        "details": signal_details,
        "count": len(signals)
    }


def get_signal_strength(signal_details: Dict) -> str:
    """
    Calculate the overall strength of detected signals.
    
    Args:
        signal_details: Dictionary containing signal details from compute_comprehensive_signals
        
    Returns:
        Signal strength as string: 'low', 'medium', 'high', or 'critical'
    """
    signal_count = signal_details.get("count", 0)
    
    if signal_count == 0:
        return "none"
    elif signal_count <= 2:
        return "low"
    elif signal_count <= 4:
        return "medium"
    elif signal_count <= 6:
        return "high"
    else:
        return "critical" 