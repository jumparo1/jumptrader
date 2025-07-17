import logging
import requests
from typing import Dict, List, Optional
from config.settings import ORION_API_KEY, ORION_BASE_URL

logger = logging.getLogger(__name__)

class OrionClient:
    """Client for fetching market data from Orion Protocol."""
    
    def __init__(self):
        self.api_key = ORION_API_KEY
        self.base_url = ORION_BASE_URL
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
            logger.info("Orion client initialized with API key")
        else:
            logger.warning("Orion API key not found - some endpoints may not work")
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Get comprehensive market data for a symbol from Orion."""
        try:
            endpoint = f"{self.base_url}/v1/market-data/{symbol}"
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Orion market data for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Orion data for {symbol}: {e}")
            return None
    
    def get_multi_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get market data for multiple symbols."""
        results = {}
        
        for symbol in symbols:
            data = self.get_market_data(symbol)
            if data:
                results[symbol] = data
        
        logger.info(f"Fetched Orion data for {len(results)} symbols")
        return results
    
    def get_liquidity_pools(self, symbol: str) -> Optional[List[Dict]]:
        """Get liquidity pool information for a symbol."""
        try:
            endpoint = f"{self.base_url}/v1/liquidity-pools/{symbol}"
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Orion liquidity pools for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Orion liquidity pools for {symbol}: {e}")
            return None
    
    def get_trading_pairs(self) -> Optional[List[Dict]]:
        """Get all available trading pairs from Orion."""
        try:
            endpoint = f"{self.base_url}/v1/trading-pairs"
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Orion trading pairs: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Orion trading pairs: {e}")
            return None
    
    def get_order_book(self, symbol: str, depth: int = 20) -> Optional[Dict]:
        """Get order book data for a symbol."""
        try:
            endpoint = f"{self.base_url}/v1/order-book/{symbol}"
            params = {"depth": depth}
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Orion order book for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Orion order book for {symbol}: {e}")
            return None
    
    def get_recent_trades(self, symbol: str, limit: int = 100) -> Optional[List[Dict]]:
        """Get recent trades for a symbol."""
        try:
            endpoint = f"{self.base_url}/v1/recent-trades/{symbol}"
            params = {"limit": limit}
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Orion recent trades for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Orion recent trades for {symbol}: {e}")
            return None
    
    def get_aggregated_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get aggregated market data for multiple symbols."""
        aggregated_data = {}
        
        for symbol in symbols:
            symbol_data = {}
            
            # Get market data
            market_data = self.get_market_data(symbol)
            if market_data:
                symbol_data.update(market_data)
            
            # Get order book
            order_book = self.get_order_book(symbol)
            if order_book:
                symbol_data['order_book'] = order_book
            
            # Get recent trades
            recent_trades = self.get_recent_trades(symbol)
            if recent_trades:
                symbol_data['recent_trades'] = recent_trades
            
            if symbol_data:
                aggregated_data[symbol] = symbol_data
        
        return aggregated_data 