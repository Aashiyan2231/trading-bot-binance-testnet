"""
Input validation for CLI-provided order parameters.

Keeping validation isolated makes it independently testable and keeps
cli.py / orders.py focused on flow rather than input-checking rules.
"""

import re

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}
# Loose symbol check: 2-12 uppercase letters/digits followed by "USDT"
# (covers BTCUSDT, ETHUSDT, 1000SHIBUSDT, etc.)
SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,12}USDT$")


class ValidationError(Exception):
    """Raised when CLI-supplied order parameters fail validation."""


def validate_symbol(symbol: str) -> str:
    symbol = (symbol or "").strip().upper()
    if not symbol:
        raise ValidationError("Symbol is required (e.g. BTCUSDT).")
    if not SYMBOL_RE.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected a USDT-M pair like BTCUSDT or ETHUSDT."
        )
    return symbol


def validate_side(side: str) -> str:
    side = (side or "").strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {sorted(VALID_SIDES)}.")
    return side


def validate_order_type(order_type: str) -> str:
    order_type = (order_type or "").strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of {sorted(VALID_ORDER_TYPES)}."
        )
    return order_type


def validate_quantity(quantity) -> float:
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.")
    if qty <= 0:
        raise ValidationError(f"Quantity must be greater than 0, got {qty}.")
    return qty


def validate_price(price, order_type: str):
    """Price is required for LIMIT and STOP_LIMIT orders, forbidden for MARKET."""
    if order_type == "MARKET":
        if price is not None:
            raise ValidationError("Price must not be supplied for MARKET orders.")
        return None

    if price is None:
        raise ValidationError(f"Price is required for {order_type} orders.")
    try:
        price_val = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be a number, got '{price}'.")
    if price_val <= 0:
        raise ValidationError(f"Price must be greater than 0, got {price_val}.")
    return price_val


def validate_stop_price(stop_price, order_type: str):
    """Stop price is required only for STOP_LIMIT orders."""
    if order_type != "STOP_LIMIT":
        if stop_price is not None:
            raise ValidationError("Stop price is only valid for STOP_LIMIT orders.")
        return None
    if stop_price is None:
        raise ValidationError("Stop price is required for STOP_LIMIT orders.")
    try:
        sp = float(stop_price)
    except (TypeError, ValueError):
        raise ValidationError(f"Stop price must be a number, got '{stop_price}'.")
    if sp <= 0:
        raise ValidationError(f"Stop price must be greater than 0, got {sp}.")
    return sp
