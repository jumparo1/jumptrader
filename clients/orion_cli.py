import json
import subprocess
import logging
from typing import Dict, Any, List, Optional
from clients.binance import get_open_interest, get_latest_funding_rate

logger = logging.getLogger(__name__)

def fetch_orion_data(symbols: List[str]) -> Dict[str, Any]:
    """
    Calls the Orion Terminal CLI in JSON mode to get all perpetuals.
    For any missing symbols, falls back to Binance REST for open interest and funding rate.
    Returns: { symbol: { 'tickCount': ..., 'fundingRate': ..., ... } }
    """
    try:
        cmd = ["clients/cli/cli", "market", "perpetuals", "--json"]
        logger.info(f"Executing Orion CLI command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        raw = json.loads(result.stdout)
        logger.info(f"Orion CLI returned {len(raw)} perpetual records")
        raw_dict = {item["symbol"]: item for item in raw}
        result_dict = {}
        missing = []
        for sym in symbols:
            if sym in raw_dict:
                result_dict[sym] = raw_dict[sym]
            else:
                missing.append(sym)
                # fallback via Binance REST
                result_dict[sym] = {
                    "tickCount":    0,
                    "fundingRate":  get_latest_funding_rate(sym),
                    "openInterest": get_open_interest(sym)
                }
        if missing:
            logger.warning(f"Orion CLI returned no data for: {missing}, used REST fallback")
        return result_dict
    except subprocess.TimeoutExpired:
        logger.error("Orion CLI command timed out after 30 seconds")
        return {}
    except subprocess.CalledProcessError as e:
        logger.error(f"Orion CLI command failed with exit code {e.returncode}")
        logger.error(f"stderr: {e.stderr}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Orion CLI JSON output: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error calling Orion CLI: {e}")
        return {}

def test_orion_cli() -> bool:
    """
    Test if the Orion CLI is available and working.
    Returns True if successful, False otherwise.
    """
    try:
        cmd = ["clients/cli/cli", "--version"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info(f"Orion CLI version: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"Orion CLI test failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Orion CLI test error: {e}")
        return False

def get_orion_perpetuals_test() -> Dict[str, Any]:
    """
    Test function to get a small sample of perpetual data.
    """
    try:
        cmd = ["clients/cli/cli", "market", "perpetuals", "--json", "--limit", "5"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            raw = json.loads(result.stdout)
            return {item["symbol"]: item for item in raw}
        else:
            logger.error(f"Orion CLI test failed: {result.stderr}")
            return {}
    except Exception as e:
        logger.error(f"Orion CLI test error: {e}")
        return {} 