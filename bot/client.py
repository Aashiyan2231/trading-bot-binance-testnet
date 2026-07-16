"""
Thin wrapper around the Binance Futures (USDT-M) Testnet REST API.

Deliberately implemented with plain `requests` + manual HMAC-SHA256 signing
rather than the python-binance SDK, so the signing/auth flow is explicit
and there is one fewer third-party dependency to install. Swapping this
module out for python-binance later would not require touching cli.py
or orders.py, since callers only depend on `place_order` / `get_server_time`.

Every outbound request and inbound response is logged. API secrets are
never logged in full.
"""

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot.client")

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW_MS = 5000
REQUEST_TIMEOUT_S = 10


class BinanceAPIError(Exception):
    """Raised when Binance returns a non-2xx / error-coded response."""

    def __init__(self, message: str, status_code: Optional[int] = None, payload: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class BinanceNetworkError(Exception):
    """Raised on connection failures, timeouts, or DNS errors."""


def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of params safe to write to logs (no signature)."""
    redacted = dict(params)
    if "signature" in redacted:
        redacted["signature"] = "***REDACTED***"
    return redacted


class BinanceFuturesTestnetClient:
    """
    Minimal REST client for Binance USDT-M Futures Testnet.

    Only implements what this bot needs: server time, and order placement
    (MARKET / LIMIT / STOP-side "STOP" for the stop-limit bonus feature).
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = DEFAULT_BASE_URL):
        if not api_key or not api_secret:
            raise ValueError(
                "API key/secret are required. Set BINANCE_TESTNET_API_KEY and "
                "BINANCE_TESTNET_API_SECRET (see README)."
            )
        self.api_key = api_key
        self.api_secret = api_secret.encode()
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # ------------------------------------------------------------------ #
    # Low-level helpers
    # ------------------------------------------------------------------ #
    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params.setdefault("recvWindow", RECV_WINDOW_MS)
        query_string = urlencode(params)
        signature = hmac.new(self.api_secret, query_string.encode(), hashlib.sha256).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        params = params or {}

        if signed:
            params = self._sign(params)

        logger.debug(
            "REQUEST %s %s params=%s", method, url, _redact(params)
        )

        try:
            response = self.session.request(
                method=method, url=url, params=params, timeout=REQUEST_TIMEOUT_S
            )
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s %s (%s)", method, url, exc)
            raise BinanceNetworkError(f"Request to {path} timed out after {REQUEST_TIMEOUT_S}s") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s %s (%s)", method, url, exc)
            raise BinanceNetworkError(f"Could not connect to {self.base_url}: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected network error: %s %s (%s)", method, url, exc)
            raise BinanceNetworkError(str(exc)) from exc

        logger.debug(
            "RESPONSE status=%s body=%s", response.status_code, response.text[:2000]
        )

        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text}

        if not response.ok:
            err_msg = body.get("msg") if isinstance(body, dict) else str(body)
            logger.error(
                "Binance API error: status=%s code=%s msg=%s",
                response.status_code,
                body.get("code") if isinstance(body, dict) else None,
                err_msg,
            )
            raise BinanceAPIError(
                message=err_msg or f"HTTP {response.status_code}",
                status_code=response.status_code,
                payload=body if isinstance(body, dict) else None,
            )

        return body

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def get_server_time(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/time")

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        """
        Place an order on /fapi/v1/order.

        order_type: MARKET, LIMIT, or STOP (Binance's stop-limit type for futures).
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force
        elif order_type == "STOP":
            # Binance futures STOP (stop-limit): needs both price and stopPrice
            params["price"] = price
            params["stopPrice"] = stop_price
            params["timeInForce"] = time_in_force

        logger.info(
            "Placing order: symbol=%s side=%s type=%s qty=%s price=%s stopPrice=%s",
            symbol, side, order_type, quantity, price, stop_price,
        )

        return self._request("POST", "/fapi/v1/order", params=params, signed=True)
