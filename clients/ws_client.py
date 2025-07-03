import asyncio
import json
import websockets
import logging

logger = logging.getLogger(__name__)

class WebSocketClient:
    def __init__(self, symbols, queue):
        # symbols: list of strings like ["BTCUSDT",…]
        # queue: an asyncio.Queue to push parsed tick data
        self.symbols = symbols
        self.queue = queue
        self.running = True

    def _build_stream_url(self):
        # Binance allows up to ~200 streams per connection
        streams = "/".join(f"{s.lower()}@aggTrade" for s in self.symbols)
        return f"wss://fstream.binance.com/stream?streams={streams}"

    async def run(self):
        url = self._build_stream_url()
        logger.info(f"Connecting to WebSocket: {url}")
        
        try:
            async with websockets.connect(url) as ws:
                logger.info("WebSocket connected successfully")
                while self.running:
                    try:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        
                        # Handle subscription confirmation
                        if "result" in data:
                            logger.info(f"Subscription confirmed: {data}")
                            continue
                            
                        # Handle trade data
                        if "data" in data:
                            tick_data = data["data"]
                            tick = {
                                "symbol": tick_data["s"],
                                "price": float(tick_data["p"]),
                                "qty": float(tick_data["q"]),
                                "timestamp": tick_data["T"]
                            }
                            await self.queue.put(tick)
                            
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("WebSocket connection closed, attempting to reconnect...")
                        break
                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            
    def stop(self):
        """Stop the WebSocket client."""
        self.running = False 