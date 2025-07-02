import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ─── Binance Configuration ─────────────────────────────────────────────────────
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', 'F7Fhhm7itvJsJfbozDvyBRNnVDCpi3wJizbtw21Z8x936npXpyDAJl8G5Fvb8Wh4')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', 'V7Of4i64f31IirRfalQrBuHa9fQcpwSNSN4x5Lq4GhuL2rTuiJ55xAg6RUnooqX3')
BINANCE_TESTNET = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'

# Binance API endpoints
BINANCE_REST_URL = "https://testnet.binancefuture.com" if BINANCE_TESTNET else "https://fapi.binance.com"
BINANCE_WS_URL = "wss://stream.binancefuture.com" if not BINANCE_TESTNET else "wss://stream.binancefuture.com"

# ─── Orion Configuration ──────────────────────────────────────────────────────
ORION_API_KEY = os.getenv('ORION_API_KEY')
ORION_BASE_URL = "https://api.orionprotocol.io"

# ─── Data Collection Settings ─────────────────────────────────────────────────
# Candle intervals and limits
CANDLE_INTERVALS = {
    '1m': {'limit': 1440, 'description': '1 minute candles for 24h'},
    '1h': {'limit': 168, 'description': '1 hour candles for 7 days'},
    '4h': {'limit': 42, 'description': '4 hour candles for 7 days'},
    '1d': {'limit': 30, 'description': 'Daily candles for 30 days'}
}

# WebSocket settings
WS_RECONNECT_DELAY = 5  # seconds
WS_HEARTBEAT_INTERVAL = 30  # seconds

# Polling intervals
ORION_POLL_INTERVAL = 15  # seconds
MARKET_DATA_REFRESH_INTERVAL = 60  # seconds

# ─── Signal Processing Settings ───────────────────────────────────────────────
# Volume spike thresholds
VOLUME_SPIKE_THRESHOLD = 2.0  # 2x average volume
VOLUME_LOOKBACK_PERIODS = 24  # hours

# Price change thresholds
PRICE_CHANGE_THRESHOLDS = {
    '1h': {'high': 5.0, 'medium': 2.0, 'low': 1.0},  # percentage
    '24h': {'high': 15.0, 'medium': 8.0, 'low': 3.0}  # percentage
}

# Momentum detection
MOMENTUM_LOOKBACK_PERIODS = 4  # hours for stair-step detection
RANGE_BREAK_THRESHOLD = 0.02  # 2% break from range

# ─── UI Settings ──────────────────────────────────────────────────────────────
DEFAULT_SYMBOLS_LIMIT = 100
MAX_SYMBOLS_DISPLAY = 500
AUTO_REFRESH_INTERVAL = 60  # seconds

# ─── Database Settings (Future) ──────────────────────────────────────────────
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///trading_data.db')

# ─── Logging Configuration ────────────────────────────────────────────────────
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ─── Feature Flags ────────────────────────────────────────────────────────────
ENABLE_WEBSOCKET = True
ENABLE_ORION_INTEGRATION = True
ENABLE_GPT_ANALYSIS = False  # Future feature
ENABLE_TELEGRAM_BOT = False  # Future feature
ENABLE_ALERTS = False  # Future feature 