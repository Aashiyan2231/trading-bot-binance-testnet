#!/usr/bin/env python3
"""
CLI entry point for the Binance Futures Testnet trading bot.

Examples
--------
Market order:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

Limit order:
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000

Stop-limit order (bonus):
    python cli.py --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.01 \\
        --price 58000 --stop-price 58500

Offline demo (no real network / API keys needed):
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --mock
"""

import argparse
import os
import sys

from bot.logging_config import setup_logging
from bot.orders import build_order_request, place_order
from bot.validators import ValidationError

logger = setup_logging()


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Place MARKET / LIMIT / STOP_LIMIT orders on Binance Futures Testnet (USDT-M).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    parser.add_argument(
        "--type", dest="order_type", required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
    )
    parser.add_argument("--quantity", required=True, help="Order quantity, e.g. 0.01")
    parser.add_argument("--price", default=None, help="Required for LIMIT / STOP_LIMIT")
    parser.add_argument("--stop-price", default=None, help="Required for STOP_LIMIT")
    parser.add_argument(
        "--base-url", default="https://testnet.binancefuture.com",
        help="Binance Futures Testnet base URL",
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Simulate the order locally instead of calling Binance (for demos/offline testing)",
    )
    return parser.parse_args(argv)


def print_summary(request) -> None:
    print("\n=== Order Request ===")
    print(f"  Symbol:      {request.symbol}")
    print(f"  Side:        {request.side}")
    print(f"  Type:        {request.order_type}")
    print(f"  Quantity:    {request.quantity}")
    if request.price is not None:
        print(f"  Price:       {request.price}")
    if request.stop_price is not None:
        print(f"  Stop Price:  {request.stop_price}")


def print_result(result) -> None:
    print("\n=== Order Response ===")
    if result.success:
        print(f"  Order ID:      {result.order_id}")
        print(f"  Status:        {result.status}")
        print(f"  Executed Qty:  {result.executed_qty}")
        print(f"  Avg Price:     {result.avg_price}")
        print("\n✅ SUCCESS: order placed.\n")
    else:
        print(f"  Error: {result.error}")
        print("\n❌ FAILED: order was not placed.\n")


def get_client(base_url: str, use_mock: bool):
    if use_mock:
        from bot.mock_client import MockBinanceFuturesTestnetClient
        return MockBinanceFuturesTestnetClient()

    from bot.client import BinanceFuturesTestnetClient

    api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
    api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
    return BinanceFuturesTestnetClient(api_key=api_key, api_secret=api_secret, base_url=base_url)


def main(argv=None) -> int:
    args = parse_args(argv)

    try:
        request = build_order_request(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValidationError as exc:
        logger.error("Validation failed: %s", exc)
        print(f"\n❌ Invalid input: {exc}\n")
        return 1

    print_summary(request)

    try:
        client = get_client(args.base_url, args.mock)
    except ValueError as exc:
        # Missing/invalid API credentials
        logger.error("Client initialization failed: %s", exc)
        print(f"\n❌ Configuration error: {exc}\n")
        return 1

    result = place_order(client, request)
    print_result(result)

    return 0 if result.success else 2


if __name__ == "__main__":
    sys.exit(main())
