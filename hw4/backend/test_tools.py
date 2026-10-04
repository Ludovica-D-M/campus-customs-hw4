"""Check every tool against `data/campus_customs.db` directly.

Each test reads the expected answer straight out of SQLite and compares it to
what the tool returned, so a tool that invented or stale-cached a value fails.
Run from the backend folder:

    python test_tools.py
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

import tools

PASSED = 0
FAILED: list[str] = []


def check(label: str, got, want) -> None:
    global PASSED
    if got == want:
        PASSED += 1
        print(f"  PASS  {label}")
    else:
        FAILED.append(label)
        print(f"  FAIL  {label}\n          got:  {got!r}\n          want: {want!r}")


def truthy(label: str, condition: bool, detail: str = "") -> None:
    global PASSED
    if condition:
        PASSED += 1
        print(f"  PASS  {label}")
    else:
        FAILED.append(label)
        print(f"  FAIL  {label}  {detail}")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(tools.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def pick_fixtures(conn: sqlite3.Connection) -> tuple[str, str, str]:
    """A real product that has both a sold-out size and an in-stock size."""
    row = conn.execute(
        """SELECT i.product_id,
                  MIN(CASE WHEN i.quantity = 0 THEN i.size END) AS sold_out,
                  MIN(CASE WHEN i.quantity > 0 THEN i.size END) AS in_stock
             FROM inventory i
            GROUP BY i.product_id
           HAVING sold_out IS NOT NULL AND in_stock IS NOT NULL
            ORDER BY i.product_id
            LIMIT 1"""
    ).fetchone()
    return row["product_id"], row["sold_out"], row["in_stock"]


def main() -> int:
    conn = db()
    product_id, sold_out_size, in_stock_size = pick_fixtures(conn)
    cat = conn.execute(
        "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
    ).fetchone()
    stock = {
        r["size"]: r["quantity"]
        for r in conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        )
    }

    print(f"\nFixture: {cat['name']}  ({product_id})")
    print(f"  stock in db: {stock}")
    print(f"  in-stock size tested: {in_stock_size}   out-of-stock size tested: {sold_out_size}\n")

    # ---------------------------------------------------------- description
    print("get_product — description")
    detail = tools.get_product(product_id)
    check("description matches the catalogue row exactly", detail.description, cat["description"])
    check("name matches", detail.name, cat["name"])
    check("garment_type matches", detail.garment_type, cat["garment_type"])
    check("colors match the stored JSON", detail.colors, json.loads(cat["colors"]))
    check("search_tags match the stored JSON", detail.search_tags, json.loads(cat["search_tags"]))
    truthy(
        "short_description is drawn from description",
        detail.description.startswith(detail.short_description.rstrip("…")[:40]),
    )

    # ---------------------------------------------------------------- price
    print("\nget_product / price_range — price")
    check("price matches the catalogue row", detail.price, float(cat["price"]))
    prices = [float(r["price"]) for r in conn.execute("SELECT price FROM catalogue")]
    overall = tools.price_range()
    check("price_range lowest", overall.lowest, min(prices))
    check("price_range highest", overall.highest, max(prices))
    check("price_range average", overall.average, round(sum(prices) / len(prices), 2))
    check("price_range count covers the whole catalogue", overall.count, len(prices))

    hoodies = [
        float(r["price"])
        for r in conn.execute("SELECT garment_type, price FROM catalogue")
        if "hood" in r["garment_type"].lower()
    ]
    hood_range = tools.price_range("hood")
    check("price_range('hood') count", hood_range.count, len(hoodies))
    check("price_range('hood') lowest", hood_range.lowest, min(hoodies))

    # ------------------------------------------------------- in-stock size
    print(f"\ncheck_size — in-stock size ({in_stock_size})")
    good = tools.check_size(product_id, in_stock_size)
    check("status", good.status, "in_stock")
    check("available", good.available, True)
    check("quantity matches inventory", good.quantity, stock[in_stock_size])
    check("price matches catalogue", good.price, float(cat["price"]))
    truthy(
        "answer states the real count",
        str(stock[in_stock_size]) in good.answer or "one left" in good.answer,
        good.answer,
    )
    truthy("answer does not say sold out", "sold out" not in good.answer.lower(), good.answer)

    # --------------------------------------------------- out-of-stock size
    print(f"\ncheck_size — out-of-stock size ({sold_out_size})")
    bad = tools.check_size(product_id, sold_out_size)
    check("status", bad.status, "out_of_stock")
    check("available", bad.available, False)
    check("quantity is 0", bad.quantity, 0)
    truthy("answer says 'sold out'", "sold out" in bad.answer.lower(), bad.answer)
    truthy("answer names the size", sold_out_size in bad.answer, bad.answer)
    truthy(
        "sold-out size is not offered as available",
        sold_out_size not in bad.other_sizes_in_stock,
        str(bad.other_sizes_in_stock),
    )
    check(
        "other_sizes_in_stock matches the inventory",
        sorted(bad.other_sizes_in_stock),
        sorted(s for s, q in stock.items() if q > 0 and s != sold_out_size),
    )

    # --------------------------------------------------- size never carried
    print("\ncheck_size — a size the shop does not carry")
    missing = tools.check_size(product_id, "XXXL")
    check("status", missing.status, "size_not_carried")
    check("quantity", missing.quantity, 0)
    truthy("answer does not call it sold out", "sold out in XXXL" not in missing.answer, missing.answer)

    # ---------------------------------------------------- card stock fields
    print("\nProductCard — stock fields")
    check(
        "sizes_in_stock matches the inventory",
        sorted(detail.sizes_in_stock),
        sorted(s for s, q in stock.items() if q > 0),
    )
    check(
        "sold_out_sizes matches the inventory",
        sorted(detail.sold_out_sizes),
        sorted(s for s, q in stock.items() if q == 0),
    )
    check("total_stock matches the inventory", detail.total_stock, sum(stock.values()))
    check("in_stock", detail.in_stock, any(q > 0 for q in stock.values()))
    truthy(
        "stock_summary names the sold-out size",
        sold_out_size in detail.stock_summary and "Sold out" in detail.stock_summary,
        detail.stock_summary,
    )

    # ----------------------------------------------- every product, no drift
    print("\nAll 102 products — tool output vs database")
    mismatched_price, mismatched_stock, mismatched_desc = [], [], []
    for row in conn.execute("SELECT * FROM catalogue"):
        card = tools.get_product(row["product_id"])
        if card.price != float(row["price"]):
            mismatched_price.append(row["product_id"])
        if card.description != row["description"]:
            mismatched_desc.append(row["product_id"])
        real = {
            r["size"]: r["quantity"]
            for r in conn.execute(
                "SELECT size, quantity FROM inventory WHERE product_id = ?", (row["product_id"],)
            )
        }
        if sorted(card.sizes_in_stock) != sorted(s for s, q in real.items() if q > 0):
            mismatched_stock.append(row["product_id"])
    check("every price matches", mismatched_price, [])
    check("every description matches", mismatched_desc, [])
    check("every in-stock size list matches", mismatched_stock, [])

    # ------------------------------------------------------------- search
    print("\nsearch_catalogue")
    result = tools.search_catalogue(query=cat["name"], limit=8)
    truthy(
        "the fixture product is found by name",
        any(p.product_id == product_id for p in result.products),
        str([p.product_id for p in result.products]),
    )
    sold_out_only = tools.search_catalogue(query="", in_stock_only=True, limit=8)
    truthy(
        "in_stock_only=True returns only buyable products",
        all(p.in_stock for p in sold_out_only.products),
    )
    zero_rows = conn.execute("SELECT COUNT(*) FROM inventory WHERE quantity = 0").fetchone()[0]
    print(f"  (note: {zero_rows} of 612 size rows are sold out; no product is sold out in all six)")

    # --------------------------------------------------------- unknown ids
    print("\nUnknown product ids")
    check("get_product returns None", tools.get_product("not-a-real-product"), None)
    check("check_size returns None", tools.check_size("not-a-real-product", "M"), None)

    # ------------------------------------- a product sold out in every size
    #
    # No product in the real database is sold out in all six sizes, so this
    # path cannot be reached with the shipped data. Run it against a throwaway
    # copy instead, so the behaviour is actually covered rather than assumed.
    print("\nA product sold out in EVERY size (temporary copy of the database)")
    original = tools.DB_PATH
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "campus_customs.db"
        shutil.copy(original, copy)
        with closing(sqlite3.connect(copy)) as scratch:
            scratch.execute(
                "UPDATE inventory SET quantity = 0 WHERE product_id = ?", (product_id,)
            )
            scratch.commit()
        tools.DB_PATH = copy
        try:
            gone = tools.get_product(product_id)
            check("in_stock is False", gone.in_stock, False)
            check("no sizes are offered", gone.sizes_in_stock, [])
            check("every size listed as sold out", sorted(gone.sold_out_sizes), sorted(stock))
            check("total_stock is 0", gone.total_stock, 0)
            truthy(
                "stock_summary says sold out in every size",
                "sold out in every size" in gone.stock_summary.lower(),
                gone.stock_summary,
            )
            size_check = tools.check_size(product_id, in_stock_size)
            check("check_size status", size_check.status, "out_of_stock")
            truthy(
                "check_size answer says sold out in every size",
                "sold out in every size" in size_check.answer.lower(),
                size_check.answer,
            )
            check("no alternative sizes offered", size_check.other_sizes_in_stock, [])
            hidden = tools.search_catalogue(query=cat["name"], in_stock_only=True, limit=8)
            truthy(
                "in_stock_only=True excludes it",
                all(p.product_id != product_id for p in hidden.products),
            )
            shown = tools.search_catalogue(query=cat["name"], in_stock_only=False, limit=8)
            truthy(
                "default search still returns it, flagged sold out",
                any(p.product_id == product_id and not p.in_stock for p in shown.products),
            )
            truthy("sold_out_matches counts it", shown.sold_out_matches >= 1)
        finally:
            tools.DB_PATH = original

    check("the real database is untouched", tools.get_product(product_id).total_stock,
          sum(stock.values()))

    # ------------------------------------------- plurals and category words
    print("\nQuery vocabulary")
    for word, where in [
        ("hoodies", "lower(garment_type) LIKE '%hood%'"),
        ("hoodie", "lower(garment_type) LIKE '%hood%'"),
        ("crewnecks", "lower(garment_type) LIKE '%crewneck%' OR lower(garment_type) LIKE '%mockneck%'"),
        ("tee", "lower(garment_type) LIKE '%t-shirt%'"),
        ("quarter-zips", "lower(garment_type) LIKE '%quarter-zip%'"),
        ("jackets", "lower(garment_type) LIKE '%jacket%' OR lower(garment_type) LIKE '%fleece%'"),
    ]:
        want = conn.execute(f"SELECT COUNT(*) FROM catalogue WHERE {where}").fetchone()[0]
        got = tools.search_catalogue(query="", garment_type=word, limit=1).count
        check(f"garment_type={word!r} finds every match", got, want)

    print("\nsearch summary wording")
    big = tools.search_catalogue(query="", garment_type="hood", limit=6)
    truthy("summary states the total, not the page size",
           str(big.count) in big.summary and "showing the first 6" in big.summary, big.summary)
    none = tools.search_catalogue(query="pink sequin ballgown", limit=6)
    check("no matches", none.count, 0)
    truthy("summary says nothing matched", "nothing" in none.summary.lower(), none.summary)

    print(f"\n{'=' * 60}")
    print(f"{PASSED} passed, {len(FAILED)} failed")
    for name in FAILED:
        print(f"  failed: {name}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
