"""
Signals module for JumpTrader.

This module contains signal detection functions for trading analysis.
"""

from .basic import (
    detect_volume_spike,
    detect_oi_jump,
    detect_funding_anomaly,
    detect_price_momentum,
    detect_volatility,
    detect_tick_spike,
    detect_near_extremes,
    compute_comprehensive_signals,
    get_signal_strength
)

__all__ = [
    "detect_volume_spike",
    "detect_oi_jump", 
    "detect_funding_anomaly",
    "detect_price_momentum",
    "detect_volatility",
    "detect_tick_spike",
    "detect_near_extremes",
    "compute_comprehensive_signals",
    "get_signal_strength"
] 