# Binance Futures Testnet Trading Bot

A small, structured Python CLI application for placing **MARKET**, **LIMIT**,
and **STOP_LIMIT** orders on **Binance Futures Testnet (USDT-M)**, with
input validation, structured logging, and clean error handling.

```
trading_bot/
  bot/
    __init__.py
    client.py         # Real Binance Futures Testnet REST client (HMAC-signed requests)
    mock_client.py     # Same interface, no network — for offline demos (--mock)
    orders.py          # Validation -> API call -> normalized OrderResult
    validators.py       # CLI input validation rules
    logging_config.py    # Rotating file + console logging setup
  tests/
    test_validators.py
  logs/
    trading_bot.log            # Full cumulative log
    sample_market_order.log     # Snapshot after a MARKET order run
    sample_limit_order.log      # Snapshot after a LIMIT order run
    sample_stop_limit_order.log  # Snapshot after a STOP_LIMIT (bonus) run
  cli.py               # CLI entry point (argparse)
  requirements.txt
  .env.example
  README.md
```

## 1. Setup

### 1.1 Get Binance Futures Testnet (Demo Trading) credentials
Binance retired the standalone `testnet.binancefuture.com` website in
August 2025 as part of a Futures Demo Trading revamp. Practice/testnet
trading is now accessed through the main Binance site:

1. Log in at https://www.binance.com with your normal Binance account
   (or create one).
2. Go to **Futures → Demo Trading** (or visit
   https://demo.binance.com directly) — you'll land on a Futures
   interface pre-loaded with a virtual USDT balance (no deposit or KYC
   needed for this practice environment).
3. Click your profile icon (top right) → **Demo Trading API** →
   generate an **API Key** and **Secret Key**. Copy both immediately;
   the Secret Key is only shown once.
4. These are practice keys only — they work against
   `https://demo-fapi.binance.com` and carry no real funds; they are
   not valid on the real Binance API.

### 1.2 Install dependencies
```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 1.3 Configure credentials
Copy `.env.example` to `.env` (or just export the variables directly) and
fill in your testnet keys:
```bash
cp .env.example .env
```
```
BINANCE_TESTNET_API_KEY=your_api_key_here
BINANCE_TESTNET_API_SECRET=your_api_secret_here
```
Then, before running the CLI, export them into your shell (the app reads
them from environment variables — it does not parse `.env` itself, to
avoid adding a dependency; use `export $(cat .env | xargs)` on
macOS/Linux, or a tool like `python-dotenv` / `direnv` if you prefer):
```bash
export BINANCE_TESTNET_API_KEY=your_api_key_here
export BINANCE_TESTNET_API_SECRET=your_api_secret_here
```

## 2. Running the bot

### Market order
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit order
```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000
```

### Stop-limit order (bonus feature)
```bash
python cli.py --symbol ETHUSDT --side SELL --type STOP_LIMIT \
  --quantity 0.5 --price 3200 --stop-price 3250
```

Each run prints an order request summary, then the order response
(orderId, status, executedQty, avgPrice), then a clear
`✅ SUCCESS` / `❌ FAILED` line. All requests, responses, and errors are
also written to `logs/trading_bot.log`.

### Offline / no-credentials demo mode
Add `--mock` to any command to exercise the full CLI → validation →
"API" → logging pipeline without making any real network call (useful
for quick smoke-testing or environments without outbound internet
access):
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --mock
```

## 3. Design notes

- **Separation of concerns**: `client.py` only knows how to talk to
  Binance's REST API (signing, HTTP, error mapping). `orders.py` only
  knows how to turn validated input into a call to that client and
  normalize the result. `cli.py` only knows how to parse arguments and
  print output. `validators.py` has zero dependencies on the other
  modules, so it's independently testable (see `tests/test_validators.py`).
- **Error handling** is layered:
  - Bad CLI input → `ValidationError`, caught in `cli.py`, printed and
    logged, exit code `1`.
  - Binance rejects the order (bad symbol, insufficient margin, etc.) →
    `BinanceAPIError`, caught in `orders.py`, returned as a failed
    `OrderResult`, exit code `2`.
  - Network/timeout issues → `BinanceNetworkError`, handled the same way.
  - Anything unexpected is caught, logged with a full traceback
    (`logger.exception`), and surfaced as a generic failure rather than
    crashing the CLI.
- **Logging**: `logs/trading_bot.log` is a rotating file handler
  (2 MB × 5 backups) capturing every outbound request (endpoint + params,
  with the HMAC signature redacted), every inbound response
  (status code + body), and every error, at `DEBUG` level. The console
  only shows `INFO`+ (order summaries and success/failure), so normal
  usage isn't noisy.

## 4. Assumptions

- **`logs/real_market_order.log` and `logs/real_limit_order.log`** were
  captured from actual orders placed against the live Binance Futures
  Demo Trading API (`https://demo-fapi.binance.com`), using real demo
  API credentials — not mock mode. `logs/sample_*.log` files are
  additional `--mock` mode runs included only to demonstrate the
  logging format offline, without needing credentials.
- Binance changed its practice-trading product between when this task
  was written and when it was completed: the old `testnet.binancefuture.com`
  website was retired in Aug 2025, replaced by `demo.binance.com` (UI)
  and `https://demo-fapi.binance.com` (API). This bot's default
  `--base-url` targets the new endpoint; override with `--base-url` if
  Binance changes it again.
- Only `BUY`/`SELL` sides and `MARKET`/`LIMIT`/`STOP_LIMIT` order types
  are supported, per the task's core + bonus scope; OCO/TWAP/Grid were
  not implemented.
- Symbol validation is a loose format check (`...USDT` suffix); it does
  not call Binance's `exchangeInfo` endpoint to verify the symbol
  actually exists or to fetch its exact quantity/price precision.
  In production, you'd fetch `/fapi/v1/exchangeInfo` once at startup and
  round `quantity`/`price` to each symbol's `stepSize`/`tickSize`.
- `recvWindow` is fixed at 5000ms and orders default to `timeInForce=GTC`
  for LIMIT/STOP_LIMIT orders (not exposed as a CLI flag, to keep the
  required argument surface minimal per the task spec).
- Credentials are read from environment variables rather than a
  committed `.env` file, so no secrets ever get checked into git.

## 5. Tests

```bash
python -m tests.test_validators
```
