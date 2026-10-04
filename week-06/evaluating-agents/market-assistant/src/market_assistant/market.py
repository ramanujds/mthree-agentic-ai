"""Seeded paper-trading sandbox: quotes, clients, holdings, cash and orders."""

import sqlite3
from datetime import date

AS_OF = date(2025, 6, 16)  # fixed "today" so holding periods are deterministic

# symbol: (name, ltp, prev_close, day_high, day_low, circuit_band_pct)
STOCKS = {
    "RELIANCE": ("Reliance Industries Ltd", 2900.00, 2880.00, 2915.50, 2872.10, 20),
    "TCS": ("Tata Consultancy Services Ltd", 3850.00, 3820.00, 3862.00, 3815.40, 20),
    "INFY": ("Infosys Ltd", 1600.00, 1612.00, 1621.30, 1594.80, 20),
    "HDFCBANK": ("HDFC Bank Ltd", 1700.00, 1695.00, 1708.90, 1690.25, 20),
    "ITC": ("ITC Ltd", 430.00, 428.50, 432.75, 427.10, 10),
    "SBIN": ("State Bank of India", 800.00, 805.00, 807.40, 796.30, 10),
}

# client_id: (name, cash)
CLIENTS = {
    "C001": ("Aarav Sharma", 500000.00),
    "C002": ("Priya Nair", 20000.00),
}

# (client_id, symbol, quantity, avg_buy_price, first_buy_date)
HOLDINGS = [
    ("C001", "RELIANCE", 50, 2500.00, "2024-03-10"),  # > 12 months: long-term
    ("C001", "TCS", 20, 3600.00, "2025-03-20"),  # < 12 months: short-term
    ("C001", "INFY", 100, 1500.00, "2024-11-05"),  # < 12 months: short-term
    ("C002", "HDFCBANK", 10, 1650.00, "2025-05-01"),
]

BROKERAGE_CAP = 20.0
BROKERAGE_PCT = 0.0003
STT_PCT = 0.001
GST_PCT = 0.18


class ToolError(Exception):
    """A domain error that is shown to the agent as an observation (e.g. order rejected)."""


def compute_charges(trade_value: float) -> dict:
    brokerage = round(min(BROKERAGE_CAP, BROKERAGE_PCT * trade_value), 2)
    stt = round(STT_PCT * trade_value, 2)
    gst = round(GST_PCT * brokerage, 2)
    return {"brokerage": brokerage, "stt": stt, "gst": gst, "total": round(brokerage + stt + gst, 2)}


class Market:
    def __init__(self, market_open: bool = True):
        self.market_open = market_open
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self._seed()

    def _seed(self) -> None:
        self.db.executescript(
            """
            CREATE TABLE clients (client_id TEXT PRIMARY KEY, name TEXT, cash REAL);
            CREATE TABLE holdings (
                client_id TEXT, symbol TEXT, quantity INTEGER,
                avg_buy_price REAL, first_buy_date TEXT,
                PRIMARY KEY (client_id, symbol)
            );
            CREATE TABLE orders (
                order_id TEXT PRIMARY KEY, client_id TEXT, symbol TEXT, side TEXT,
                quantity INTEGER, price REAL, trade_value REAL, charges REAL, placed_on TEXT
            );
            """
        )
        self.db.executemany(
            "INSERT INTO clients VALUES (?, ?, ?)", [(cid, n, c) for cid, (n, c) in CLIENTS.items()]
        )
        self.db.executemany("INSERT INTO holdings VALUES (?, ?, ?, ?, ?)", HOLDINGS)
        self.db.commit()

    # ---- reads -------------------------------------------------------------------------

    def get_quote(self, symbol: str) -> dict:
        symbol = symbol.strip().upper()
        if symbol not in STOCKS:
            raise ToolError(
                f"Symbol '{symbol}' not found on NSE. Tradable symbols: {', '.join(STOCKS)}"
            )
        name, ltp, prev, high, low, band = STOCKS[symbol]
        return {
            "symbol": symbol,
            "name": name,
            "ltp": ltp,
            "prev_close": prev,
            "day_high": high,
            "day_low": low,
            "circuit_band_pct": band,
            "upper_circuit": round(prev * (1 + band / 100), 2),
            "lower_circuit": round(prev * (1 - band / 100), 2),
            "market_status": "OPEN" if self.market_open else "CLOSED",
        }

    def _client(self, client_id: str) -> sqlite3.Row:
        row = self.db.execute(
            "SELECT * FROM clients WHERE client_id = ?", (client_id.strip().upper(),)
        ).fetchone()
        if row is None:
            raise ToolError(f"Client '{client_id}' not found")
        return row

    def get_portfolio(self, client_id: str) -> dict:
        client = self._client(client_id)
        rows = self.db.execute(
            "SELECT * FROM holdings WHERE client_id = ? ORDER BY symbol", (client["client_id"],)
        ).fetchall()
        holdings = [
            {
                "symbol": r["symbol"],
                "quantity": r["quantity"],
                "avg_buy_price": r["avg_buy_price"],
                "first_buy_date": r["first_buy_date"],
                "holding_days": (AS_OF - date.fromisoformat(r["first_buy_date"])).days,
            }
            for r in rows
        ]
        return {
            "client_id": client["client_id"],
            "name": client["name"],
            "cash_balance": round(client["cash"], 2),
            "holdings": holdings,
        }

    def snapshot(self) -> dict:
        """Full state of the sandbox, for before/after diffs in evals."""
        return {
            "clients": {r["client_id"]: round(r["cash"], 2) for r in self.db.execute("SELECT * FROM clients")},
            "holdings": {
                (r["client_id"], r["symbol"]): r["quantity"]
                for r in self.db.execute("SELECT * FROM holdings")
            },
            "orders": [dict(r) for r in self.db.execute("SELECT * FROM orders ORDER BY order_id")],
        }

    # ---- writes ------------------------------------------------------------------------

    def place_order(self, client_id: str, symbol: str, quantity: int, side: str) -> dict:
        """Market delivery order at the last traded price. No duplicate guard on purpose, so evals can catch repeats."""
        side = side.strip().upper()
        if side not in ("BUY", "SELL"):
            raise ToolError("side must be BUY or SELL")
        if quantity < 1:
            raise ToolError("Order rejected: minimum quantity is 1 share")
        if not self.market_open:
            raise ToolError("Order rejected: market is closed (NSE trades Mon-Fri 9:15 AM to 3:30 PM IST)")

        client = self._client(client_id)
        quote = self.get_quote(symbol)
        cid, sym, price = client["client_id"], quote["symbol"], quote["ltp"]
        value = round(price * quantity, 2)
        charges = compute_charges(value)

        held = self.db.execute(
            "SELECT * FROM holdings WHERE client_id = ? AND symbol = ?", (cid, sym)
        ).fetchone()

        if side == "BUY":
            needed = round(value + charges["total"], 2)
            if client["cash"] < needed:
                raise ToolError(
                    f"Order rejected: insufficient funds. Required Rs. {needed:.2f}, "
                    f"available Rs. {client['cash']:.2f}"
                )
            new_cash = round(client["cash"] - needed, 2)
            if held:
                total_qty = held["quantity"] + quantity
                avg = round((held["avg_buy_price"] * held["quantity"] + value) / total_qty, 2)
                self.db.execute(
                    "UPDATE holdings SET quantity = ?, avg_buy_price = ? WHERE client_id = ? AND symbol = ?",
                    (total_qty, avg, cid, sym),
                )
            else:
                self.db.execute(
                    "INSERT INTO holdings VALUES (?, ?, ?, ?, ?)", (cid, sym, quantity, price, AS_OF.isoformat())
                )
        else:
            have = held["quantity"] if held else 0
            if have < quantity:
                raise ToolError(
                    f"Order rejected: insufficient holdings. Trying to sell {quantity} {sym}, you hold {have}"
                )
            new_cash = round(client["cash"] + value - charges["total"], 2)
            if have == quantity:
                self.db.execute("DELETE FROM holdings WHERE client_id = ? AND symbol = ?", (cid, sym))
            else:
                self.db.execute(
                    "UPDATE holdings SET quantity = ? WHERE client_id = ? AND symbol = ?",
                    (have - quantity, cid, sym),
                )

        self.db.execute("UPDATE clients SET cash = ? WHERE client_id = ?", (new_cash, cid))
        n = self.db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] + 1
        order_id = f"ORD-{n:04d}"
        self.db.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (order_id, cid, sym, side, quantity, price, value, charges["total"], AS_OF.isoformat()),
        )
        self.db.commit()
        return {
            "order_id": order_id,
            "status": "EXECUTED",
            "client_id": cid,
            "symbol": sym,
            "side": side,
            "quantity": quantity,
            "price": price,
            "trade_value": value,
            "charges": charges,
            "cash_balance_after": new_cash,
        }
