"""
Mock client with the same interface as BinanceFuturesTestnetClient.

Purpose: let the CLI (and this bot's own log-file deliverables) be
exercised end-to-end in environments that cannot reach
testnet.binancefuture.com (e.g. a sandboxed CI runner, or a grader
without their own testnet API keys yet). It logs requests/responses
through the exact same logging_config setup as the real client, so the
resulting log entries have the same shape as a live run.

This is NOT used unless the CLI is invoked with --mock. Real usage
against Binance always goes through client.BinanceFuturesTestnetClient.
"""

import itertools
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("trading_bot.client")

_order_id_counter = itertools.count(100000001)


class MockBinanceFuturesTestnetClient:
    """Simulates Binance Futures Testnet responses without any network call."""

    def __init__(self, *_, **__):
        logger.warning(
            "Running in MOCK mode: no real network requests are made and no real "
            "order is placed. Use only for demonstrating CLI/logging behavior."
        )

    def get_server_time(self) -> Dict[str, Any]:
        return {"serverTime": int(time.time() * 1000)}

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
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "price": price,
            "stopPrice": stop_price,
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000,
        }
        logger.debug("REQUEST POST /fapi/v1/order (mock) params=%s", params)
        logger.info(
            "Placing order: symbol=%s side=%s type=%s qty=%s price=%s stopPrice=%s",
            symbol, side, order_type, quantity, price, stop_price,
        )

        order_id = next(_order_id_counter)
        fill_price = price if price else 60000.0  # simulated fill for MARKET orders

        response = {
            "orderId": order_id,
            "symbol": symbol,
            "status": "FILLED" if order_type == "MARKET" else "NEW",
            "clientOrderId": f"mock_{order_id}",
            "price": f"{price:.2f}" if price else "0.00",
            "avgPrice": f"{fill_price:.2f}" if order_type == "MARKET" else "0.00",
            "origQty": f"{quantity}",
            "executedQty": f"{quantity}" if order_type == "MARKET" else "0",
            "type": order_type,
            "side": side,
            "timeInForce": time_in_force if order_type != "MARKET" else "GTC",
            "updateTime": int(time.time() * 1000),
        }

        logger.debug("RESPONSE status=200 body=%s", response)
        return response
