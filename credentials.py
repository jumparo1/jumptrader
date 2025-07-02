import os
from dotenv import load_dotenv
from binance.client import Client

def get_binance_client():
    """
    Load environment variables and return an initialized Binance client.
    
    Returns:
        Client: Initialized Binance client with API credentials
        
    Raises:
        ValueError: If API credentials are not found in environment variables
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API credentials from environment variables
    api_key = os.getenv('BINANCE_API_KEY', 'F7Fhhm7itvJsJfbozDvyBRNnVDCpi3wJizbtw21Z8x936npXpyDAJl8G5Fvb8Wh4')
    api_secret = os.getenv('BINANCE_API_SECRET', 'V7Of4i64f31IirRfalQrBuHa9fQcpwSNSN4x5Lq4GhuL2rTuiJ55xAg6RUnooqX3')
    
    # Validate that credentials are provided
    if not api_key or not api_secret:
        raise ValueError(
            "BINANCE_API_KEY and BINANCE_API_SECRET must be set in environment variables or .env file"
        )
    
    # Initialize and return the Binance client
    client = Client(api_key, api_secret)
    return client

def test_connection():
    """
    Test the Binance API connection by fetching futures account balance.
    This function demonstrates how to use the client.
    """
    try:
        client = get_binance_client()
        
        # Test with futures account balance (requires API key with futures permissions)
        balance = client.futures_account_balance()
        
        print("✅ Successfully connected to Binance API!")
        print(f"📊 Futures Account Balance:")
        for asset in balance:
            if float(asset['balance']) > 0:
                print(f"  {asset['asset']}: {asset['balance']} (Available: {asset['availableBalance']})")
        
        return client
        
    except Exception as e:
        print(f"❌ Error connecting to Binance API: {e}")
        return None

if __name__ == "__main__":
    # Test the connection when run directly
    test_connection() 