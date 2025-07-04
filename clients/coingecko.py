from dotenv import load_dotenv
import os
import requests
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def fetch_coingecko_data(symbols: list[str]) -> dict[str, dict]:
    """
    Fetch CoinGecko data for given Binance symbols.
    
    Args:
        symbols: List of Binance symbols (e.g., ['BTCUSDT', 'ETHUSDT'])
        
    Returns:
        Dict mapping symbols to their CoinGecko data with keys:
        - market_cap: float
        - fdv: float (fully diluted valuation)
    """
    # Get API key from environment
    api_key = os.getenv("COINGECKO_API_KEY", "CG-tAhqifbeGmbb9nJ8k6ACeDdM")
    
    # For debugging, try without API key first
    headers = {}
    if api_key and api_key != "CG-tAhqifbeGmbb9nJ8k6ACeDdM":
        headers = {"X-CG-Pro-API-Key": api_key}
    
    # Convert Binance symbols to CoinGecko IDs
    symbol_to_id = {}
    coingecko_ids = []
    
    # CoinGecko ID mapping for common symbols
    symbol_mapping = {
        'BTCUSDT': 'bitcoin',
        'ETHUSDT': 'ethereum',
        'ADAUSDT': 'cardano',
        'BNBUSDT': 'binancecoin',
        'XRPUSDT': 'ripple',
        'SOLUSDT': 'solana',
        'DOTUSDT': 'polkadot',
        'DOGEUSDT': 'dogecoin',
        'AVAXUSDT': 'avalanche-2',
        'LINKUSDT': 'chainlink',
        'LTCUSDT': 'litecoin',
        'BCHUSDT': 'bitcoin-cash',
        'UNIUSDT': 'uniswap',
        'ATOMUSDT': 'cosmos',
        'ETCUSDT': 'ethereum-classic',
        'XLMUSDT': 'stellar',
        'TRXUSDT': 'tron',
        'FILUSDT': 'filecoin',
        'NEARUSDT': 'near',
        'ALGOUSDT': 'algorand'
    }
    
    for symbol in symbols:
        # Use mapping if available, otherwise try simple conversion
        if symbol in symbol_mapping:
            coingecko_id = symbol_mapping[symbol]
        else:
            # Remove 'USDT' and convert to lowercase as fallback
            coingecko_id = symbol.replace('USDT', '').lower()
        
        coingecko_ids.append(coingecko_id)
        symbol_to_id[symbol] = coingecko_id
    
    if not coingecko_ids:
        return {}
    
    # Prepare API request - using Coins Markets endpoint
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(coingecko_ids),
        "order": "market_cap_desc",
        "per_page": len(coingecko_ids),
        "page": 1,
        "sparkline": "false"
    }
    
    try:
        logger.info(f"Making CoinGecko API request to: {url}")
        logger.info(f"Parameters: {params}")
        logger.info(f"Headers: {headers}")
        
        response = requests.get(url, headers=headers, params=params)
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Response text: {response.text}")
            
        response.raise_for_status()
        data = response.json()
        
        # Create a mapping from CoinGecko ID to data
        id_to_data = {item["id"]: item for item in data}
        
        # Process response
        result = {}
        for symbol in symbols:
            coingecko_id = symbol_to_id[symbol]
            
            if coingecko_id in id_to_data:
                coin_data = id_to_data[coingecko_id]
                result[symbol] = {
                    "market_cap": float(coin_data.get("market_cap") or 0),
                    "fdv": float(coin_data.get("fully_diluted_valuation") or 0),
                }
            else:
                logger.warning(f"CoinGecko returned no data for {symbol} (ID: {coingecko_id})")
                result[symbol] = {
                    "market_cap": 0.0,
                    "fdv": 0.0
                }
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching CoinGecko data: {e}")
        # Return empty data for all symbols on error
        return {symbol: {"market_cap": 0.0, "fdv": 0.0} for symbol in symbols}
    except Exception as e:
        logger.error(f"Unexpected error in fetch_coingecko_data: {e}")
        return {symbol: {"market_cap": 0.0, "fdv": 0.0} for symbol in symbols}


if __name__ == "__main__":
    # Test the function
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    print("Testing CoinGecko API...")
    print(f"Symbols: {test_symbols}")
    
    result = fetch_coingecko_data(test_symbols)
    
    print("\nResults:")
    for symbol, data in result.items():
        print(f"{symbol}:")
        print(f"  Market Cap: ${data['market_cap']:,.0f}")
        print(f"  FDV: ${data['fdv']:,.0f}")
        if data['fdv'] > 0:
            ratio = (data['market_cap'] / data['fdv']) * 100
            print(f"  Circ/FDV Ratio: {ratio:.1f}%")
        print() 