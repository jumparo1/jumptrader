import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)

def format_number(value: float, decimals: int = 2, prefix: str = "", suffix: str = "") -> str:
    """Format a number with appropriate suffixes (K, M, B)."""
    if value is None or value == 0:
        return f"{prefix}0{suffix}"
    
    if abs(value) >= 1e9:
        return f"{prefix}{value/1e9:.{decimals}f}B{suffix}"
    elif abs(value) >= 1e6:
        return f"{prefix}{value/1e6:.{decimals}f}M{suffix}"
    elif abs(value) >= 1e3:
        return f"{prefix}{value/1e3:.{decimals}f}K{suffix}"
    else:
        return f"{prefix}{value:.{decimals}f}{suffix}"

def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a percentage value."""
    if value is None:
        return "-"
    return f"{value:+.{decimals}f}%"

def format_price(value: float, decimals: int = 4) -> str:
    """Format a price value."""
    if value is None:
        return "-"
    return f"${value:,.{decimals}f}"

def calculate_change_percentage(current: float, previous: float) -> Optional[float]:
    """Calculate percentage change between two values."""
    if previous == 0 or previous is None or current is None:
        return None
    return ((current - previous) / previous) * 100

def detect_anomalies(data: List[float], threshold: float = 2.0) -> List[int]:
    """Detect anomalies in a time series using z-score method."""
    if len(data) < 3:
        return []
    
    df = pd.DataFrame(data)
    z_scores = abs((df - df.mean()) / df.std())
    anomalies = z_scores > threshold
    
    return [i for i, is_anomaly in enumerate(anomalies[0]) if is_anomaly]

def calculate_moving_average(data: List[float], window: int) -> List[Optional[float]]:
    """Calculate moving average for a list of values."""
    if len(data) < window:
        return [None] * len(data)
    
    result = []
    for i in range(len(data)):
        if i < window - 1:
            result.append(None)
        else:
            window_data = data[i - window + 1:i + 1]
            result.append(sum(window_data) / len(window_data))
    
    return result

def calculate_volatility(data: List[float], window: int = 20) -> List[Optional[float]]:
    """Calculate rolling volatility for a list of values."""
    if len(data) < window:
        return [None] * len(data)
    
    result = []
    for i in range(len(data)):
        if i < window - 1:
            result.append(None)
        else:
            window_data = data[i - window + 1:i + 1]
            returns = []
            for j in range(1, len(window_data)):
                if window_data[j-1] != 0:
                    returns.append((window_data[j] - window_data[j-1]) / window_data[j-1])
            
            if returns:
                volatility = (sum(r**2 for r in returns) / len(returns)) ** 0.5
                result.append(volatility)
            else:
                result.append(None)
    
    return result

def retry_on_failure(func, max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry a function on failure."""
    def wrapper(*args, **kwargs):
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    sleep_time = delay * (backoff ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
        
        logger.error(f"All {max_retries} attempts failed for {func.__name__}: {last_exception}")
        raise last_exception
    
    return wrapper

def rate_limit(requests_per_second: float = 10):
    """Decorator to implement rate limiting."""
    def decorator(func):
        last_call_time = 0
        min_interval = 1.0 / requests_per_second
        
        def wrapper(*args, **kwargs):
            nonlocal last_call_time
            current_time = time.time()
            
            time_since_last_call = current_time - last_call_time
            if time_since_last_call < min_interval:
                sleep_time = min_interval - time_since_last_call
                time.sleep(sleep_time)
            
            last_call_time = time.time()
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def validate_symbol(symbol: str) -> bool:
    """Validate if a symbol follows Binance format."""
    if not symbol or len(symbol) < 3:
        return False
    
    # Basic validation - should be alphanumeric and contain at least one letter
    if not symbol.replace('USDT', '').replace('BUSD', '').replace('BTC', '').replace('ETH', '').isalnum():
        return False
    
    return True

def parse_timeframe(timeframe: str) -> Optional[int]:
    """Parse timeframe string to seconds."""
    timeframe_map = {
        '1m': 60,
        '3m': 180,
        '5m': 300,
        '15m': 900,
        '30m': 1800,
        '1h': 3600,
        '2h': 7200,
        '4h': 14400,
        '6h': 21600,
        '8h': 28800,
        '12h': 43200,
        '1d': 86400,
        '3d': 259200,
        '1w': 604800,
        '1M': 2592000
    }
    
    return timeframe_map.get(timeframe)

def get_timeframe_description(timeframe: str) -> str:
    """Get human-readable description of a timeframe."""
    descriptions = {
        '1m': '1 minute',
        '3m': '3 minutes',
        '5m': '5 minutes',
        '15m': '15 minutes',
        '30m': '30 minutes',
        '1h': '1 hour',
        '2h': '2 hours',
        '4h': '4 hours',
        '6h': '6 hours',
        '8h': '8 hours',
        '12h': '12 hours',
        '1d': '1 day',
        '3d': '3 days',
        '1w': '1 week',
        '1M': '1 month'
    }
    
    return descriptions.get(timeframe, timeframe)

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe file system operations."""
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    return filename

def create_backup_filename(base_name: str, extension: str = '.json') -> str:
    """Create a backup filename with timestamp."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{base_name}_{timestamp}{extension}"

def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Merge two dictionaries, with dict2 values taking precedence."""
    result = dict1.copy()
    result.update(dict2)
    return result

def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries."""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split a list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def flatten_list(nested_list: List) -> List:
    """Flatten a nested list."""
    flattened = []
    for item in nested_list:
        if isinstance(item, list):
            flattened.extend(flatten_list(item))
        else:
            flattened.append(item)
    return flattened

def get_unique_values(data: List[Dict], key: str) -> List:
    """Get unique values for a specific key from a list of dictionaries."""
    return list(set(item.get(key) for item in data if item.get(key) is not None))

def sort_dict_by_value(d: Dict, reverse: bool = True) -> Dict:
    """Sort a dictionary by its values."""
    return dict(sorted(d.items(), key=lambda x: x[1], reverse=reverse))

def filter_dict_by_keys(d: Dict, keys: List) -> Dict:
    """Filter a dictionary to only include specified keys."""
    return {k: v for k, v in d.items() if k in keys}

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator 