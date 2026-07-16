"""
Order placement logic: ties together validation + the API client, and
shapes the client's raw response into a small, consistent result object
that the CLI layer can print without knowing anything about Binance's
JSON schema.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from bot.client import BinanceAPIError, BinanceNetworkError
from bot.validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

logger = logging.getLogger("trading_bot.orders")


@dataclass
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str] = None
    status: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    raw_response: Optional[dict] = None
    error: Optional[str] = None


def build_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity,
    price=None,
    stop_price=None,
) -> OrderRequest:
    """Validate raw CLI input and return a clean OrderRequest, or raise ValidationError."""
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    order_type = validate_order_type(order_type)
    quantity = validate_quantity(quantity)
    price = validate_price(price, order_type if order_type != "STOP_LIMIT" else "LIMIT")
    stop_price = validate_stop_price(stop_price, order_type)

    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
    )


def place_order(client, request: OrderRequest) -> OrderResult:
    """
    Submit `request` via `client` (either the real Binance client or the
    mock client — both share the same `place_order` signature) and
    return a normalized OrderResult. Never raises: all failure modes are
    captured and returned as OrderResult(success=False, error=...).
    """
    # Binance's futures API type for a stop-limit order is "STOP"
    api_order_type = "STOP" if request.order_type == "STOP_LIMIT" else request.order_type

    try:
        response = client.place_order(
            symbol=request.symbol,
            side=request.side,
            order_type=api_order_type,
            quantity=request.quantity,
            price=request.price,
            stop_price=request.stop_price,
        )
    except BinanceAPIError as exc:
        logger.error("Order rejected by Binance: %s", exc)
        return OrderResult(success=False, error=f"API error: {exc}")
    except BinanceNetworkError as exc:
        logger.error("Network failure while placing order: %s", exc)
        return OrderResult(success=False, error=f"Network error: {exc}")
    except Exception as exc:  # noqa: BLE001 - last-resort safety net, logged with traceback
        logger.exception("Unexpected error while placing order")
        return OrderResult(success=False, error=f"Unexpected error: {exc}")

    result = OrderResult(
        success=True,
        order_id=str(response.get("orderId")),
        status=response.get("status"),
        executed_qty=response.get("executedQty"),
        avg_price=response.get("avgPrice"),
        raw_response=response,
    )
    logger.info(
        "Order placed successfully: orderId=%s status=%s executedQty=%s avgPrice=%s",
        result.order_id, result.status, result.executed_qty, result.avg_price,
    )
    return result
