import requests
import pandas as pd

FUTURES_OPEN_INTEREST = "https://fapi.binance.com/fapi/v1/openInterest"
FUTURES_FUNDING_RATE = "https://fapi.binance.com/fapi/v1/fundingRate"
KLINES = "https://fapi.binance.com/fapi/v1/klines"

def get_open_interest(symbol: str) -> float:
    r = requests.get(FUTURES_OPEN_INTEREST, params={"symbol": symbol}).json()
    return float(r.get("openInterest", 0.0))

def get_latest_funding_rate(symbol: str) -> float:
    # get most recent funding rate
    r = requests.get(FUTURES_FUNDING_RATE, params={"symbol": symbol, "limit": 1}).json()
    if isinstance(r, list) and r:
        return float(r[0].get("fundingRate", 0.0))
    return 0.0

def get_btc_correlation(symbol: str) -> float:
    """
    Compute Pearson correlation (abs) between 1h returns of symbol and BTCUSDT
    over the last 168 candles.
    """
    def fetch_close(sym):
        params = {"symbol": sym, "interval": "1h", "limit": 168}
        data = requests.get(KLINES, params=params).json()
        return [float(candle[4]) for candle in data]

    sym_closes = fetch_close(symbol)
    btc_closes = fetch_close("BTCUSDT")
    if len(sym_closes) < 2 or len(btc_closes) < 2:
        return 0.0
    s_ret = pd.Series(sym_closes).pct_change().dropna()
    b_ret = pd.Series(btc_closes).pct_change().dropna()
    corr = s_ret.corr(b_ret)
    return round(abs(corr) if corr is not None else 0.0, 2) 