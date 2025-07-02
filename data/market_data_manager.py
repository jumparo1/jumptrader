import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import pandas as pd

from clients.binance_client import BinanceDataClient
from clients.orion_client import OrionClient
from config.settings import (
    CANDLE_INTERVALS, ORION_POLL_INTERVAL, MARKET_DATA_REFRESH_INTERVAL,
    ENABLE_WEBSOCKET, ENABLE_ORION_INTEGRATION
)

logger = logging.getLogger(__name__)

class MarketDataManager:
    """Manages data collection from multiple sources (Binance, Orion, etc.)."""
    
    def __init__(self):
        self.binance_client = BinanceDataClient()
        self.orion_client = OrionClient() if ENABLE_ORION_INTEGRATION else None
        
        # Data storage
        self.market_data = {}
        self.klines_data = {}
        self.ticker_data = {}
        self.open_interest_data = {}
        self.funding_rates = {}
        
        # Callbacks for data updates
        self.data_callbacks = []
        
        # Control flags
        self.is_running = False
        self.last_update = {}
        
        logger.info("MarketDataManager initialized")
    
    def add_data_callback(self, callback: Callable):
        """Add a callback function to be called when new data arrives."""
        self.data_callbacks.append(callback)
    
    def remove_data_callback(self, callback: Callable):
        """Remove a callback function."""
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
    
    def _notify_callbacks(self, data_type: str, data: Dict):
        """Notify all registered callbacks of new data."""
        for callback in self.data_callbacks:
            try:
                callback(data_type, data)
            except Exception as e:
                logger.error(f"Error in data callback: {e}")
    
    def get_perpetual_symbols(self) -> List[str]:
        """Get all available perpetual contract symbols."""
        return self.binance_client.get_perpetual_symbols()
    
    async def fetch_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch comprehensive market data for multiple symbols."""
        logger.info(f"Fetching market data for {len(symbols)} symbols")
        
        market_data = {}
        
        # Fetch data in batches to avoid rate limits
        batch_size = 50
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            # Fetch 24h ticker data
            for symbol in batch:
                ticker_data = self.binance_client.get_24h_ticker(symbol)
                if ticker_data:
                    market_data[symbol] = ticker_data
                    
                    # Add additional data
                    oi_data = self.binance_client.get_open_interest(symbol)
                    if oi_data:
                        market_data[symbol]['open_interest'] = oi_data
                    
                    funding_data = self.binance_client.get_funding_rate(symbol)
                    if funding_data:
                        market_data[symbol]['funding_rate'] = funding_data
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        # Store the data
        self.market_data.update(market_data)
        self.last_update['market_data'] = datetime.now()
        
        # Notify callbacks
        self._notify_callbacks('market_data', market_data)
        
        logger.info(f"Fetched market data for {len(market_data)} symbols")
        return market_data
    
    async def fetch_klines_data(self, symbols: List[str], intervals: List[str] = None) -> Dict[str, Dict]:
        """Fetch klines/candlestick data for multiple symbols and intervals."""
        if intervals is None:
            intervals = ['1m', '1h']
        
        logger.info(f"Fetching klines data for {len(symbols)} symbols, intervals: {intervals}")
        
        klines_data = {}
        
        for symbol in symbols:
            symbol_klines = {}
            
            for interval in intervals:
                if interval in CANDLE_INTERVALS:
                    limit = CANDLE_INTERVALS[interval]['limit']
                    klines = self.binance_client.get_klines(symbol, interval, limit)
                    
                    if klines:
                        symbol_klines[interval] = klines
            
            if symbol_klines:
                klines_data[symbol] = symbol_klines
        
        # Store the data
        self.klines_data.update(klines_data)
        self.last_update['klines_data'] = datetime.now()
        
        # Notify callbacks
        self._notify_callbacks('klines_data', klines_data)
        
        logger.info(f"Fetched klines data for {len(klines_data)} symbols")
        return klines_data
    
    async def fetch_orion_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch market data from Orion Protocol."""
        if not self.orion_client:
            logger.warning("Orion client not available")
            return {}
        
        logger.info(f"Fetching Orion data for {len(symbols)} symbols")
        
        orion_data = self.orion_client.get_aggregated_data(symbols)
        
        # Store the data
        self.last_update['orion_data'] = datetime.now()
        
        # Notify callbacks
        self._notify_callbacks('orion_data', orion_data)
        
        logger.info(f"Fetched Orion data for {len(orion_data)} symbols")
        return orion_data
    
    async def websocket_ticker_callback(self, data: Dict):
        """Callback for WebSocket ticker updates."""
        symbol = data.get('s')
        if symbol:
            # Update ticker data
            self.ticker_data[symbol] = data
            self.last_update['ticker_data'] = datetime.now()
            
            # Notify callbacks
            self._notify_callbacks('ticker_update', {symbol: data})
    
    async def websocket_kline_callback(self, data: Dict):
        """Callback for WebSocket kline updates."""
        symbol = data.get('s')
        interval = data.get('k', {}).get('i')
        
        if symbol and interval:
            # Update klines data
            if symbol not in self.klines_data:
                self.klines_data[symbol] = {}
            
            if interval not in self.klines_data[symbol]:
                self.klines_data[symbol][interval] = []
            
            # Add new kline
            kline_data = {
                "timestamp": data['k']['t'],
                "open": float(data['k']['o']),
                "high": float(data['k']['h']),
                "low": float(data['k']['l']),
                "close": float(data['k']['c']),
                "volume": float(data['k']['v']),
                "close_time": data['k']['T'],
                "quote_volume": float(data['k']['q']),
                "trades": int(data['k']['n']),
                "taker_buy_volume": float(data['k']['V']),
                "taker_buy_quote_volume": float(data['k']['Q'])
            }
            
            # Replace last kline if it's the same timestamp, otherwise append
            if (self.klines_data[symbol][interval] and 
                self.klines_data[symbol][interval][-1]['timestamp'] == kline_data['timestamp']):
                self.klines_data[symbol][interval][-1] = kline_data
            else:
                self.klines_data[symbol][interval].append(kline_data)
            
            # Keep only the last N klines to prevent memory issues
            max_klines = CANDLE_INTERVALS.get(interval, {}).get('limit', 1000)
            if len(self.klines_data[symbol][interval]) > max_klines:
                self.klines_data[symbol][interval] = self.klines_data[symbol][interval][-max_klines:]
            
            self.last_update['klines_data'] = datetime.now()
            
            # Notify callbacks
            self._notify_callbacks('kline_update', {symbol: {interval: kline_data}})
    
    async def start_websocket_streams(self, symbols: List[str]):
        """Start WebSocket streams for real-time data."""
        if not ENABLE_WEBSOCKET:
            logger.info("WebSocket streams disabled")
            return
        
        logger.info(f"Starting WebSocket streams for {len(symbols)} symbols")
        
        await self.binance_client.start_websocket_streams(
            symbols,
            ticker_callback=self.websocket_ticker_callback,
            kline_callback=self.websocket_kline_callback
        )
    
    def stop_websocket_streams(self):
        """Stop WebSocket streams."""
        if ENABLE_WEBSOCKET:
            self.binance_client.stop_websocket_streams()
            logger.info("WebSocket streams stopped")
    
    async def start_data_collection(self, symbols: List[str]):
        """Start continuous data collection."""
        self.is_running = True
        logger.info(f"Starting data collection for {len(symbols)} symbols")
        
        # Start WebSocket streams
        await self.start_websocket_streams(symbols)
        
        # Initial data fetch
        await self.fetch_market_data(symbols)
        await self.fetch_klines_data(symbols)
        
        if self.orion_client:
            await self.fetch_orion_data(symbols)
        
        # Start periodic data collection
        asyncio.create_task(self._periodic_market_data(symbols))
        asyncio.create_task(self._periodic_orion_data(symbols))
    
    async def _periodic_market_data(self, symbols: List[str]):
        """Periodically fetch market data."""
        while self.is_running:
            try:
                await asyncio.sleep(MARKET_DATA_REFRESH_INTERVAL)
                if self.is_running:
                    await self.fetch_market_data(symbols)
            except Exception as e:
                logger.error(f"Error in periodic market data collection: {e}")
    
    async def _periodic_orion_data(self, symbols: List[str]):
        """Periodically fetch Orion data."""
        if not self.orion_client:
            return
        
        while self.is_running:
            try:
                await asyncio.sleep(ORION_POLL_INTERVAL)
                if self.is_running:
                    await self.fetch_orion_data(symbols)
            except Exception as e:
                logger.error(f"Error in periodic Orion data collection: {e}")
    
    def stop_data_collection(self):
        """Stop all data collection."""
        self.is_running = False
        self.stop_websocket_streams()
        logger.info("Data collection stopped")
    
    def get_latest_data(self, data_type: str = 'market_data') -> Dict:
        """Get the latest data of a specific type."""
        if data_type == 'market_data':
            return self.market_data
        elif data_type == 'klines_data':
            return self.klines_data
        elif data_type == 'ticker_data':
            return self.ticker_data
        else:
            return {}
    
    def get_data_age(self, data_type: str) -> Optional[timedelta]:
        """Get the age of the last update for a data type."""
        if data_type in self.last_update:
            return datetime.now() - self.last_update[data_type]
        return None
    
    def export_to_dataframe(self, symbols: List[str] = None) -> pd.DataFrame:
        """Export market data to a pandas DataFrame."""
        if symbols is None:
            symbols = list(self.market_data.keys())
        
        rows = []
        for symbol in symbols:
            if symbol in self.market_data:
                data = self.market_data[symbol].copy()
                data['symbol'] = symbol
                rows.append(data)
        
        return pd.DataFrame(rows)
    
    def start_data_collection_sync(self, symbols: list):
        """Synchronous wrapper to run async data collection in a thread."""
        import asyncio
        asyncio.run(self.start_data_collection(symbols)) 