import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Callable
import websockets
import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException

from config.settings import (
    BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_REST_URL,
    BINANCE_WS_URL, CANDLE_INTERVALS, WS_RECONNECT_DELAY
)

logger = logging.getLogger(__name__)

class BinanceDataClient:
    """Comprehensive Binance data client for REST API and WebSocket streams."""
    
    def __init__(self):
        self.client = None
        self.ws_connections = {}
        self.callbacks = {}
        self.is_running = False
        
        if BINANCE_API_KEY and BINANCE_API_SECRET:
            self.client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
            logger.info("Binance client initialized with API credentials")
        else:
            logger.warning("Binance API credentials not found - using public endpoints only")
    
    def get_perpetual_symbols(self) -> List[str]:
        """Get all available perpetual contract symbols."""
        try:
            exchange_info = requests.get(f"{BINANCE_REST_URL}/fapi/v1/exchangeInfo", timeout=10).json()
            symbols = [
                s["symbol"] for s in exchange_info["symbols"]
                if s["contractType"] == "PERPETUAL" and s["status"] == "TRADING"
            ]
            logger.info(f"Found {len(symbols)} perpetual symbols")
            return symbols
        except Exception as e:
            logger.error(f"Error fetching perpetual symbols: {e}")
            return []
    
    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> List[Dict]:
        """Fetch kline/candlestick data for a symbol."""
        try:
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            response = requests.get(f"{BINANCE_REST_URL}/fapi/v1/klines", params=params, timeout=5)
            response.raise_for_status()
            
            klines = response.json()
            formatted_klines = []
            
            for kline in klines:
                formatted_klines.append({
                    "timestamp": kline[0],
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5]),
                    "close_time": kline[6],
                    "quote_volume": float(kline[7]),
                    "trades": int(kline[8]),
                    "taker_buy_volume": float(kline[9]),
                    "taker_buy_quote_volume": float(kline[10])
                })
            
            return formatted_klines
            
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return []
    
    def get_24h_ticker(self, symbol: str) -> Optional[Dict]:
        """Get 24-hour ticker statistics for a symbol."""
        try:
            params = {"symbol": symbol}
            response = requests.get(f"{BINANCE_REST_URL}/fapi/v1/ticker/24hr", params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            return {
                "symbol": data["symbol"],
                "price_change": float(data["priceChange"]),
                "price_change_percent": float(data["priceChangePercent"]),
                "weighted_avg_price": float(data["weightedAvgPrice"]),
                "prev_close_price": float(data.get("prevClosePrice", data["openPrice"])),
                "last_price": float(data["lastPrice"]),
                "last_qty": float(data["lastQty"]),
                "bid_price": float(data.get("bidPrice", data["lastPrice"])),
                "ask_price": float(data.get("askPrice", data["lastPrice"])),
                "open_price": float(data["openPrice"]),
                "high_price": float(data["highPrice"]),
                "low_price": float(data["lowPrice"]),
                "volume": float(data["volume"]),
                "quote_volume": float(data["quoteVolume"]),
                "open_time": data["openTime"],
                "close_time": data["closeTime"],
                "count": data["count"]
            }
            
        except Exception as e:
            logger.error(f"Error fetching 24h ticker for {symbol}: {e}")
            return None
    
    def get_open_interest(self, symbol: str) -> Optional[Dict]:
        """Get open interest for a symbol."""
        try:
            params = {"symbol": symbol}
            response = requests.get(f"{BINANCE_REST_URL}/fapi/v1/openInterest", params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            return {
                "symbol": data["symbol"],
                "open_interest": float(data["openInterest"]),
                "timestamp": data["time"]
            }
            
        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            return None
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict]:
        """Get current funding rate for a symbol."""
        try:
            params = {"symbol": symbol, "limit": 1}
            response = requests.get(f"{BINANCE_REST_URL}/fapi/v1/fundingRate", params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            # Handle list response from Binance API
            if isinstance(data, list) and data:
                data = data[0]  # Get the first (most recent) funding rate
            else:
                return None
                
            return {
                "symbol": data["symbol"],
                "funding_rate": float(data["fundingRate"]),
                "funding_time": data["fundingTime"],
                "next_funding_time": data.get("nextFundingTime", 0)
            }
            
        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol}: {e}")
            return None
    
    async def subscribe_ticker_stream(self, symbols: List[str], callback: Callable):
        """Subscribe to real-time ticker streams for multiple symbols."""
        if not symbols:
            return
        
        # Binance WebSocket has a limit of 200 streams per connection
        chunk_size = 200
        symbol_chunks = [symbols[i:i + chunk_size] for i in range(0, len(symbols), chunk_size)]
        
        for i, chunk in enumerate(symbol_chunks):
            stream_name = f"ticker_chunk_{i}"
            await self._subscribe_stream(chunk, "ticker", stream_name, callback)
    
    async def subscribe_kline_stream(self, symbols: List[str], interval: str, callback: Callable):
        """Subscribe to real-time kline streams for multiple symbols."""
        if not symbols:
            return
        
        chunk_size = 200
        symbol_chunks = [symbols[i:i + chunk_size] for i in range(0, len(symbols), chunk_size)]
        
        for i, chunk in enumerate(symbol_chunks):
            stream_name = f"kline_{interval}_chunk_{i}"
            await self._subscribe_stream(chunk, f"kline_{interval}", stream_name, callback)
    
    async def _subscribe_stream(self, symbols: List[str], stream_type: str, connection_name: str, callback: Callable):
        """Subscribe to a specific stream type for given symbols."""
        streams = [f"{symbol.lower()}@{stream_type}" for symbol in symbols]
        stream_url = f"{BINANCE_WS_URL}/stream?streams={'/'.join(streams)}"
        
        self.callbacks[connection_name] = callback
        
        async def websocket_handler():
            while self.is_running:
                try:
                    async with websockets.connect(stream_url) as websocket:
                        logger.info(f"Connected to {stream_type} stream for {len(symbols)} symbols")
                        
                        while self.is_running:
                            try:
                                message = await websocket.recv()
                                data = json.loads(message)
                                
                                if 'data' in data:
                                    await callback(data['data'])
                                    
                            except websockets.exceptions.ConnectionClosed:
                                logger.warning(f"WebSocket connection closed for {connection_name}")
                                break
                            except Exception as e:
                                logger.error(f"Error processing WebSocket message: {e}")
                                
                except Exception as e:
                    logger.error(f"WebSocket connection error for {connection_name}: {e}")
                
                if self.is_running:
                    logger.info(f"Reconnecting to {connection_name} in {WS_RECONNECT_DELAY} seconds...")
                    await asyncio.sleep(WS_RECONNECT_DELAY)
        
        # Start the WebSocket handler
        asyncio.create_task(websocket_handler())
    
    async def start_websocket_streams(self, symbols: List[str], ticker_callback: Callable = None, kline_callback: Callable = None):
        """Start all WebSocket streams."""
        self.is_running = True
        
        if ticker_callback:
            await self.subscribe_ticker_stream(symbols, ticker_callback)
        
        if kline_callback:
            for interval in ['1m', '1h']:
                await self.subscribe_kline_stream(symbols, interval, kline_callback)
        
        logger.info("WebSocket streams started")
    
    def stop_websocket_streams(self):
        """Stop all WebSocket streams."""
        self.is_running = False
        logger.info("WebSocket streams stopped")
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information (requires API credentials)."""
        if not self.client:
            logger.warning("Cannot get account info - no API credentials")
            return None
        
        try:
            account_info = self.client.futures_account()
            return account_info
        except BinanceAPIException as e:
            logger.error(f"Binance API error getting account info: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    def get_position_info(self) -> List[Dict]:
        """Get position information (requires API credentials)."""
        if not self.client:
            logger.warning("Cannot get position info - no API credentials")
            return []
        
        try:
            positions = self.client.futures_position_information()
            return [pos for pos in positions if float(pos['positionAmt']) != 0]
        except BinanceAPIException as e:
            logger.error(f"Binance API error getting positions: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return [] 