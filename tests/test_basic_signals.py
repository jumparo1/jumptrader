"""
Unit tests for basic signal detection functions.

This module tests all signal detection functions in signals.basic
with various edge cases and normal behavior scenarios.
"""

import pytest
import sys
import os

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signals.basic import (
    detect_volume_spike,
    detect_oi_jump,
    detect_funding_anomaly,
    detect_price_momentum,
    detect_volatility,
    detect_tick_spike,
    detect_near_extremes,
    compute_basic_signals,
    compute_comprehensive_signals,
    get_signal_strength
)


class TestVolumeSpike:
    """Test volume spike detection functionality."""
    
    def test_volume_spike_detected(self):
        """Test that volume spike is detected when current volume is above threshold."""
        assert detect_volume_spike(2000, 1000) == True
        assert detect_volume_spike(3000, 1000, threshold=2.5) == True
    
    def test_volume_spike_not_detected(self):
        """Test that volume spike is not detected when below threshold."""
        assert detect_volume_spike(1500, 1000, threshold=2.0) == False
        assert detect_volume_spike(1800, 1000, threshold=2.0) == False
    
    def test_edge_cases(self):
        """Test edge cases for volume spike detection."""
        # Zero average volume
        assert detect_volume_spike(1000, 0) == False
        
        # Negative values
        assert detect_volume_spike(-1000, 1000) == False
        assert detect_volume_spike(1000, -1000) == False
        
        # Zero current volume
        assert detect_volume_spike(0, 1000) == False


class TestOIJump:
    """Test open interest jump detection functionality."""
    
    def test_oi_jump_detected(self):
        """Test that OI jump is detected when current OI is above threshold."""
        assert detect_oi_jump(1500, 1000) == True
        assert detect_oi_jump(2000, 1000, threshold=1.8) == True
    
    def test_oi_jump_not_detected(self):
        """Test that OI jump is not detected when below threshold."""
        assert detect_oi_jump(1000, 1000) == False
        assert detect_oi_jump(1200, 1000, threshold=1.5) == False
    
    def test_edge_cases(self):
        """Test edge cases for OI jump detection."""
        # Zero previous OI
        assert detect_oi_jump(1000, 0) == False
        
        # Negative values
        assert detect_oi_jump(-1000, 1000) == False
        assert detect_oi_jump(1000, -1000) == False
        
        # Zero current OI
        assert detect_oi_jump(0, 1000) == False


class TestFundingAnomaly:
    """Test funding rate anomaly detection functionality."""
    
    def test_funding_anomaly_detected_positive(self):
        """Test that positive funding anomaly is detected."""
        assert detect_funding_anomaly(0.06) == True
        assert detect_funding_anomaly(0.10) == True
    
    def test_funding_anomaly_detected_negative(self):
        """Test that negative funding anomaly is detected."""
        assert detect_funding_anomaly(-0.07) == True
        assert detect_funding_anomaly(-0.15) == True
    
    def test_funding_anomaly_not_detected(self):
        """Test that funding anomaly is not detected when within normal range."""
        assert detect_funding_anomaly(0.02) == False
        assert detect_funding_anomaly(-0.03) == False
        assert detect_funding_anomaly(0.0) == False
    
    def test_custom_threshold(self):
        """Test funding anomaly detection with custom threshold."""
        assert detect_funding_anomaly(0.03, threshold=0.02) == True
        assert detect_funding_anomaly(0.01, threshold=0.02) == False


class TestPriceMomentum:
    """Test price momentum detection functionality."""
    
    def test_bullish_momentum(self):
        """Test that bullish momentum is detected."""
        detected, direction = detect_price_momentum(5.0)
        assert detected == True
        assert direction == "bullish"
        
        detected, direction = detect_price_momentum(10.0, threshold=5.0)
        assert detected == True
        assert direction == "bullish"
    
    def test_bearish_momentum(self):
        """Test that bearish momentum is detected."""
        detected, direction = detect_price_momentum(-4.0)
        assert detected == True
        assert direction == "bearish"
        
        detected, direction = detect_price_momentum(-8.0, threshold=5.0)
        assert detected == True
        assert direction == "bearish"
    
    def test_neutral_momentum(self):
        """Test that neutral momentum is detected when within threshold."""
        detected, direction = detect_price_momentum(2.0)
        assert detected == False
        assert direction == "neutral"
        
        detected, direction = detect_price_momentum(-1.0)
        assert detected == False
        assert direction == "neutral"
        
        detected, direction = detect_price_momentum(0.0)
        assert detected == False
        assert direction == "neutral"


class TestVolatility:
    """Test volatility detection functionality."""
    
    def test_high_volatility_detected(self):
        """Test that high volatility is detected."""
        assert detect_volatility(15.0) == True
        assert detect_volatility(-20.0) == True
        assert detect_volatility(25.0, threshold=20.0) == True
    
    def test_low_volatility_not_detected(self):
        """Test that low volatility is not detected."""
        assert detect_volatility(5.0) == False
        assert detect_volatility(-8.0) == False
        assert detect_volatility(0.0) == False
    
    def test_custom_threshold(self):
        """Test volatility detection with custom threshold."""
        assert detect_volatility(8.0, threshold=5.0) == True
        assert detect_volatility(3.0, threshold=5.0) == False


class TestTickSpike:
    """Test tick spike detection functionality."""
    
    def test_tick_spike_detected(self):
        """Test that tick spike is detected."""
        assert detect_tick_spike(101.0, 100.0) == True  # 1% increase
        assert detect_tick_spike(99.0, 100.0) == True   # 1% decrease
        assert detect_tick_spike(100.5, 100.0, threshold=0.3) == True
    
    def test_tick_spike_not_detected(self):
        """Test that tick spike is not detected when change is small."""
        assert detect_tick_spike(100.3, 100.0) == False  # 0.3% change
        assert detect_tick_spike(99.8, 100.0) == False   # 0.2% change
    
    def test_edge_cases(self):
        """Test edge cases for tick spike detection."""
        # Zero last price
        assert detect_tick_spike(100.0, 0.0) == False
        
        # Negative values
        assert detect_tick_spike(-100.0, 100.0) == False
        assert detect_tick_spike(100.0, -100.0) == False
        
        # Zero current price
        assert detect_tick_spike(0.0, 100.0) == False


class TestNearExtremes:
    """Test near extremes detection functionality."""
    
    def test_near_high_detected(self):
        """Test that near high is detected."""
        detected, position = detect_near_extremes(99.0, 100.0, 90.0)
        assert detected == True
        assert position == "near_high"
    
    def test_near_low_detected(self):
        """Test that near low is detected."""
        detected, position = detect_near_extremes(90.5, 100.0, 90.0)
        assert detected == True
        assert position == "near_low"
    
    def test_middle_position(self):
        """Test that middle position is detected when not near extremes."""
        detected, position = detect_near_extremes(95.0, 100.0, 90.0)
        assert detected == False
        assert position == "middle"
    
    def test_edge_cases(self):
        """Test edge cases for near extremes detection."""
        # Zero prices
        detected, position = detect_near_extremes(100.0, 0.0, 90.0)
        assert detected == False
        assert position == "middle"
        
        detected, position = detect_near_extremes(100.0, 100.0, 0.0)
        assert detected == False
        assert position == "middle"
        
        # Negative values
        detected, position = detect_near_extremes(-100.0, 100.0, 90.0)
        assert detected == False
        assert position == "middle"


class TestComputeComprehensiveSignals:
    """Test comprehensive signal computation functionality."""
    
    def test_no_signals(self):
        """Test when no signals are detected."""
        row_data = {
            "quoteVolume": 100_000_000,  # Below threshold
            "openInterest": 50_000_000,   # Below threshold
            "fundingRate": 0.02,          # Below threshold
            "change_1h": 1.0,             # Below threshold
            "priceChangePercent": 5.0,    # Below threshold
            "lastPrice": 100.0,
            "highPrice": 110.0,
            "lowPrice": 90.0,
            "last_tick_price": 100.1      # Below threshold
        }
        
        result = compute_comprehensive_signals(row_data)
        assert result["count"] == 0
        assert result["signal_string"] == "-"
        assert len(result["signals"]) == 0
    
    def test_multiple_signals(self):
        """Test when multiple signals are detected."""
        row_data = {
            "quoteVolume": 600_000_000,   # Above threshold
            "openInterest": 150_000_000,  # Above threshold
            "fundingRate": 0.06,          # Above threshold
            "change_1h": 5.0,             # Above threshold
            "priceChangePercent": 15.0,   # Above threshold
            "lastPrice": 100.0,
            "highPrice": 100.5,           # Near high
            "lowPrice": 90.0,
            "last_tick_price": 100.6      # Above threshold
        }
        
        result = compute_comprehensive_signals(row_data)
        assert result["count"] >= 5  # Should detect multiple signals
        assert result["signal_string"] != "-"
        assert len(result["signals"]) >= 5
    
    def test_signal_details(self):
        """Test that signal details are properly captured."""
        row_data = {
            "quoteVolume": 600_000_000,
            "fundingRate": 0.06,
            "change_1h": 5.0,
            "lastPrice": 100.0,
            "highPrice": 110.0,
            "lowPrice": 90.0
        }
        
        result = compute_comprehensive_signals(row_data)
        
        # Check that details are captured
        assert "volume_spike" in result["details"]
        assert "funding_anomaly" in result["details"]
        assert "price_momentum" in result["details"]
        
        # Check specific details
        volume_details = result["details"]["volume_spike"]
        assert volume_details["detected"] == True
        assert volume_details["volume"] == 600_000_000


class TestSignalStrength:
    """Test signal strength calculation functionality."""
    
    def test_no_signals(self):
        """Test signal strength when no signals are detected."""
        signal_details = {"count": 0}
        strength = get_signal_strength(signal_details)
        assert strength == "none"
    
    def test_low_strength(self):
        """Test low signal strength."""
        signal_details = {"count": 1}
        strength = get_signal_strength(signal_details)
        assert strength == "low"
        
        signal_details = {"count": 2}
        strength = get_signal_strength(signal_details)
        assert strength == "low"
    
    def test_medium_strength(self):
        """Test medium signal strength."""
        signal_details = {"count": 3}
        strength = get_signal_strength(signal_details)
        assert strength == "medium"
        
        signal_details = {"count": 4}
        strength = get_signal_strength(signal_details)
        assert strength == "medium"
    
    def test_high_strength(self):
        """Test high signal strength."""
        signal_details = {"count": 5}
        strength = get_signal_strength(signal_details)
        assert strength == "high"
        
        signal_details = {"count": 6}
        strength = get_signal_strength(signal_details)
        assert strength == "high"
    
    def test_critical_strength(self):
        """Test critical signal strength."""
        signal_details = {"count": 7}
        strength = get_signal_strength(signal_details)
        assert strength == "critical"
        
        signal_details = {"count": 10}
        strength = get_signal_strength(signal_details)
        assert strength == "critical"


class TestComputeBasicSignals:
    """Test the compute_basic_signals function."""
    
    @pytest.mark.parametrize("chg1h,chg24h,vol24h,expected", [
        (1, 0, 1e9, ["🔥 Volume Spike"]),  
        (6, 0, 1e7, ["📈 1H Gainer"]),      
        (0, 12, 1e7, ["⚠️ Volatile"]),     
        (10, 15, 1e9, ["🔥 Volume Spike","📈 1H Gainer","⚠️ Volatile"]),  
        (0, 0, 1e6, []),                    
    ])
    def test_compute_basic_signals(self, chg1h, chg24h, vol24h, expected):
        """Test compute_basic_signals with various input combinations."""
        tags = compute_basic_signals(chg1h, chg24h, vol24h)
        assert set(tags) == set(expected)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"]) 