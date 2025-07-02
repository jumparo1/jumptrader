import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from config.settings import (
    VOLUME_SPIKE_THRESHOLD, VOLUME_LOOKBACK_PERIODS,
    PRICE_CHANGE_THRESHOLDS, MOMENTUM_LOOKBACK_PERIODS,
    RANGE_BREAK_THRESHOLD
)

logger = logging.getLogger(__name__)

class SignalProcessor:
    """Processes market data to generate trading signals."""
    
    def __init__(self):
        self.signal_history = {}
        self.volume_baselines = {}
        
        logger.info("SignalProcessor initialized")
    
    def process_market_data(self, market_data: Dict[str, Dict], klines_data: Dict[str, Dict] = None) -> Dict[str, List[str]]:
        """Process market data and generate signals for all symbols."""
        signals = {}
        
        for symbol, data in market_data.items():
            symbol_signals = []
            
            # Get klines data for this symbol if available
            symbol_klines = klines_data.get(symbol, {}) if klines_data else {}
            
            # Generate different types of signals
            volume_signals = self._detect_volume_spikes(symbol, data, symbol_klines)
            price_signals = self._detect_price_movements(symbol, data, symbol_klines)
            momentum_signals = self._detect_momentum_patterns(symbol, symbol_klines)
            range_signals = self._detect_range_breaks(symbol, symbol_klines)
            
            # Combine all signals
            symbol_signals.extend(volume_signals)
            symbol_signals.extend(price_signals)
            symbol_signals.extend(momentum_signals)
            symbol_signals.extend(range_signals)
            
            signals[symbol] = symbol_signals
        
        # Store signal history
        self.signal_history[datetime.now()] = signals
        
        return signals
    
    def _detect_volume_spikes(self, symbol: str, market_data: Dict, klines_data: Dict) -> List[str]:
        """Detect volume spikes based on historical volume data."""
        signals = []
        
        try:
            current_volume = market_data.get('quote_volume', 0)
            
            if not current_volume:
                return signals
            
            # Get historical volume data from klines
            if '1h' in klines_data:
                hourly_klines = klines_data['1h']
                if len(hourly_klines) >= VOLUME_LOOKBACK_PERIODS:
                    # Calculate average volume over lookback period
                    recent_volumes = [k['quote_volume'] for k in hourly_klines[-VOLUME_LOOKBACK_PERIODS:]]
                    avg_volume = np.mean(recent_volumes)
                    
                    if avg_volume > 0:
                        volume_ratio = current_volume / avg_volume
                        
                        if volume_ratio >= VOLUME_SPIKE_THRESHOLD:
                            signals.append(f"🔥 Volume Spike ({volume_ratio:.1f}x)")
                        elif volume_ratio >= VOLUME_SPIKE_THRESHOLD * 0.7:
                            signals.append(f"📈 High Volume ({volume_ratio:.1f}x)")
            
            # Store baseline for future reference
            self.volume_baselines[symbol] = current_volume
            
        except Exception as e:
            logger.error(f"Error detecting volume spikes for {symbol}: {e}")
        
        return signals
    
    def _detect_price_movements(self, symbol: str, market_data: Dict, klines_data: Dict) -> List[str]:
        """Detect significant price movements."""
        signals = []
        
        try:
            # 24h price change
            price_change_24h = market_data.get('price_change_percent', 0)
            
            if abs(price_change_24h) >= PRICE_CHANGE_THRESHOLDS['24h']['high']:
                direction = "📈" if price_change_24h > 0 else "📉"
                signals.append(f"{direction} Major Move 24h ({price_change_24h:+.1f}%)")
            elif abs(price_change_24h) >= PRICE_CHANGE_THRESHOLDS['24h']['medium']:
                direction = "📈" if price_change_24h > 0 else "📉"
                signals.append(f"{direction} Strong Move 24h ({price_change_24h:+.1f}%)")
            
            # 1h price change (from klines if available)
            if '1h' in klines_data and len(klines_data['1h']) >= 2:
                recent_klines = klines_data['1h'][-2:]
                if len(recent_klines) == 2:
                    prev_close = recent_klines[0]['close']
                    current_close = recent_klines[1]['close']
                    
                    if prev_close > 0:
                        price_change_1h = ((current_close - prev_close) / prev_close) * 100
                        
                        if abs(price_change_1h) >= PRICE_CHANGE_THRESHOLDS['1h']['high']:
                            direction = "🚀" if price_change_1h > 0 else "💥"
                            signals.append(f"{direction} Major Move 1h ({price_change_1h:+.1f}%)")
                        elif abs(price_change_1h) >= PRICE_CHANGE_THRESHOLDS['1h']['medium']:
                            direction = "📈" if price_change_1h > 0 else "📉"
                            signals.append(f"{direction} Strong Move 1h ({price_change_1h:+.1f}%)")
            
        except Exception as e:
            logger.error(f"Error detecting price movements for {symbol}: {e}")
        
        return signals
    
    def _detect_momentum_patterns(self, symbol: str, klines_data: Dict) -> List[str]:
        """Detect momentum patterns like stair-step movements."""
        signals = []
        
        try:
            if '1h' in klines_data and len(klines_data['1h']) >= MOMENTUM_LOOKBACK_PERIODS:
                hourly_klines = klines_data['1h'][-MOMENTUM_LOOKBACK_PERIODS:]
                
                # Check for consecutive green/red candles
                consecutive_green = 0
                consecutive_red = 0
                
                for kline in hourly_klines:
                    if kline['close'] > kline['open']:
                        consecutive_green += 1
                        consecutive_red = 0
                    elif kline['close'] < kline['open']:
                        consecutive_red += 1
                        consecutive_green = 0
                    else:
                        consecutive_green = 0
                        consecutive_red = 0
                
                if consecutive_green >= 3:
                    signals.append(f"🟢 Stair-Step Up ({consecutive_green}h)")
                elif consecutive_red >= 3:
                    signals.append(f"🔴 Stair-Step Down ({consecutive_red}h)")
                
                # Check for momentum acceleration
                if len(hourly_klines) >= 4:
                    recent_klines = hourly_klines[-4:]
                    volumes = [k['quote_volume'] for k in recent_klines]
                    
                    if len(volumes) >= 4:
                        # Check if volume is increasing
                        if volumes[-1] > volumes[-2] > volumes[-3] > volumes[-4]:
                            signals.append("📊 Volume Acceleration")
                        
                        # Check if price movement is accelerating
                        price_changes = []
                        for i in range(1, len(recent_klines)):
                            prev_close = recent_klines[i-1]['close']
                            curr_close = recent_klines[i]['close']
                            if prev_close > 0:
                                change = ((curr_close - prev_close) / prev_close) * 100
                                price_changes.append(abs(change))
                        
                        if len(price_changes) >= 3:
                            if price_changes[-1] > price_changes[-2] > price_changes[-3]:
                                signals.append("⚡ Momentum Acceleration")
            
        except Exception as e:
            logger.error(f"Error detecting momentum patterns for {symbol}: {e}")
        
        return signals
    
    def _detect_range_breaks(self, symbol: str, klines_data: Dict) -> List[str]:
        """Detect range breaks and consolidation patterns."""
        signals = []
        
        try:
            if '1h' in klines_data and len(klines_data['1h']) >= 24:
                # Look at last 24 hours
                recent_klines = klines_data['1h'][-24:]
                
                # Calculate range
                highs = [k['high'] for k in recent_klines]
                lows = [k['low'] for k in recent_klines]
                
                range_high = max(highs)
                range_low = min(lows)
                range_mid = (range_high + range_low) / 2
                
                if range_high > range_low:
                    range_size = (range_high - range_low) / range_mid
                    
                    # Check if current price is breaking out of range
                    current_price = recent_klines[-1]['close']
                    
                    if current_price > range_high * (1 + RANGE_BREAK_THRESHOLD):
                        signals.append(f"🚀 Range Break Up ({range_size:.1%} range)")
                    elif current_price < range_low * (1 - RANGE_BREAK_THRESHOLD):
                        signals.append(f"💥 Range Break Down ({range_size:.1%} range)")
                    
                    # Check for tight range (consolidation)
                    if range_size < 0.02:  # Less than 2% range
                        signals.append("📐 Tight Range")
                    elif range_size < 0.05:  # Less than 5% range
                        signals.append("📏 Consolidation")
            
        except Exception as e:
            logger.error(f"Error detecting range breaks for {symbol}: {e}")
        
        return signals
    
    def get_signal_summary(self, signals: Dict[str, List[str]]) -> Dict[str, int]:
        """Get a summary of signal types across all symbols."""
        summary = {}
        
        for symbol, symbol_signals in signals.items():
            for signal in symbol_signals:
                # Extract signal type from emoji
                if "🔥" in signal:
                    summary['volume_spikes'] = summary.get('volume_spikes', 0) + 1
                elif "📈" in signal or "📉" in signal:
                    summary['price_moves'] = summary.get('price_moves', 0) + 1
                elif "🟢" in signal or "🔴" in signal:
                    summary['momentum'] = summary.get('momentum', 0) + 1
                elif "🚀" in signal or "💥" in signal:
                    summary['breakouts'] = summary.get('breakouts', 0) + 1
                elif "📊" in signal or "⚡" in signal:
                    summary['acceleration'] = summary.get('acceleration', 0) + 1
                elif "📐" in signal or "📏" in signal:
                    summary['consolidation'] = summary.get('consolidation', 0) + 1
        
        return summary
    
    def get_top_signals(self, signals: Dict[str, List[str]], top_n: int = 10) -> List[Tuple[str, List[str]]]:
        """Get symbols with the most signals."""
        symbol_signal_counts = [(symbol, len(symbol_signals)) for symbol, symbol_signals in signals.items()]
        symbol_signal_counts.sort(key=lambda x: x[1], reverse=True)
        
        top_symbols = symbol_signal_counts[:top_n]
        return [(symbol, signals[symbol]) for symbol, _ in top_symbols]
    
    def filter_signals_by_type(self, signals: Dict[str, List[str]], signal_type: str) -> Dict[str, List[str]]:
        """Filter signals by type (e.g., 'volume', 'momentum', 'breakout')."""
        filtered = {}
        
        for symbol, symbol_signals in signals.items():
            filtered_signals = []
            for signal in symbol_signals:
                if signal_type.lower() in signal.lower():
                    filtered_signals.append(signal)
            
            if filtered_signals:
                filtered[symbol] = filtered_signals
        
        return filtered
    
    def get_signal_history(self, hours: int = 24) -> Dict[str, List[str]]:
        """Get signal history for the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_signals = {}
        for timestamp, signals in self.signal_history.items():
            if timestamp >= cutoff_time:
                for symbol, symbol_signals in signals.items():
                    if symbol not in recent_signals:
                        recent_signals[symbol] = []
                    recent_signals[symbol].extend(symbol_signals)
        
        return recent_signals 