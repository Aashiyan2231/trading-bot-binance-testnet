"""
Lightweight tests for bot.validators — run with: python -m tests.test_validators
(kept dependency-free so `pytest` isn't a hard requirement, though it will
also work fine under pytest if installed.)
"""

from bot.validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)


def expect_error(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except ValidationError:
        return True
    return False


def test_valid_symbol():
    assert validate_symbol("btcusdt") == "BTCUSDT"
    assert validate_symbol("ETHUSDT") == "ETHUSDT"


def test_invalid_symbol():
    assert expect_error(validate_symbol, "")
    assert expect_error(validate_symbol, "BTC-USD")
    assert expect_error(validate_symbol, "BTC")


def test_side():
    assert validate_side("buy") == "BUY"
    assert validate_side("SELL") == "SELL"
    assert expect_error(validate_side, "HOLD")


def test_order_type():
    assert validate_order_type("market") == "MARKET"
    assert expect_error(validate_order_type, "ICEBERG")


def test_quantity():
    assert validate_quantity("0.01") == 0.01
    assert expect_error(validate_quantity, "0")
    assert expect_error(validate_quantity, "-1")
    assert expect_error(validate_quantity, "abc")


def test_price_required_for_limit():
    assert expect_error(validate_price, None, "LIMIT")
    assert validate_price("65000", "LIMIT") == 65000.0


def test_price_forbidden_for_market():
    assert validate_price(None, "MARKET") is None
    assert expect_error(validate_price, "100", "MARKET")


def test_stop_price():
    assert validate_stop_price(None, "LIMIT") is None
    assert expect_error(validate_stop_price, None, "STOP_LIMIT")
    assert validate_stop_price("58500", "STOP_LIMIT") == 58500.0


if __name__ == "__main__":
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError:
            failed += 1
            print(f"FAIL  {t.__name__}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
