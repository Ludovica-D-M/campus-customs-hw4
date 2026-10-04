"""Catalogue lookups the agent can call.

Every one of these reads `data/campus_customs.db` directly. They are plain
functions here; `agent.py` registers them as PydanticAI tools. Keeping them
separate means the same lookups back both the agent and the REST endpoints,
so the chat and the Products page can never disagree about stock.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import certifi
from dotenv import load_dotenv

from pydantic import ValidationError

from models import (
    CategorySummary,
    ChatMessage,
    SizeSearchResult,
    PriceRange,
    ProductCard,
    ProductDetail,
    SearchResult,
    SizeAvailability,
    SizeStock,
)

BACKEND_DIR = Path(__file__).resolve().parent
HW4_DIR = BACKEND_DIR.parent
DATA_DIR = HW4_DIR / "data"
DB_PATH = DATA_DIR / "campus_customs.db"

# Portkey gateway. The model is a 5.6-series model, as the assignment requires.
MODEL_NAME = "gpt-5.6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

# `garment_type` is inconsistent in the data, so each category is a list of
# substrings rather than an exact value.
CATEGORIES: list[tuple[str, list[str]]] = [
    ("Hoodies", ["hood"]),
    ("Crewnecks", ["crewneck", "mockneck"]),
    ("T-shirts", ["t-shirt"]),
    ("Quarter-zips", ["quarter-zip"]),
    ("Jackets & fleece", ["jacket", "fleece"]),
    ("Performance", ["performance"]),
]

MAX_SEARCH_RESULTS = 8

# A shopper's word for a category is not the word in the data. "hoodie" as a
# plain substring misses "hooded sweatshirt" — four of the shop's 27 hoodies —
# so a category filter is expanded to the needles for whichever category it
# names before it is matched.
GARMENT_SYNONYMS: dict[str, list[str]] = {
    "hoodie": ["hood"],
    "hoody": ["hood"],
    "hooded": ["hood"],
    "sweatshirt": ["hood", "crewneck", "mockneck"],
    "crewneck": ["crewneck", "mockneck"],
    "crew": ["crewneck", "mockneck"],
    "mockneck": ["mockneck"],
    "tee": ["t-shirt"],
    "t-shirt": ["t-shirt"],
    "tshirt": ["t-shirt"],
    "shirt": ["t-shirt", "performance"],
    "quarter-zip": ["quarter-zip"],
    "quarter zip": ["quarter-zip"],
    "1/4 zip": ["quarter-zip"],
    "zip": ["quarter-zip", "full-zip"],
    "jacket": ["jacket", "fleece"],
    "fleece": ["jacket", "fleece"],
    "outerwear": ["jacket", "fleece"],
    "performance": ["performance"],
}


def expand_garment_type(garment_type: str) -> list[str]:
    """Turn a shopper's category word into the substrings the data uses."""
    needles: list[str] = []
    for raw in garment_type.split(","):
        word = term_variants(raw.strip().lower())[-1] if raw.strip() else ""
        if not word:
            continue
        needles.extend(GARMENT_SYNONYMS.get(word, [word]))
    return list(dict.fromkeys(needles))


# ---------------------------------------------------------------- setup


def use_certifi_tls() -> None:
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())


def load_api_key() -> str:
    """Read PORTKEY_API_KEY from HW4 or any parent project folder.

    The key is only ever read from the environment — it is never written into
    source, logged, or returned by any endpoint.
    """
    for folder in (HW4_DIR, *HW4_DIR.parents):
        env_file = folder / ".env"
        if env_file.is_file():
            load_dotenv(env_file, override=False)
    key = os.getenv("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError(
            "PORTKEY_API_KEY was not found in HW4 or its parent project folders."
        )
    return key


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------------------- conversion


def parse_json_list(raw: Any) -> list[str]:
    """`colors` and `search_tags` are JSON arrays stored in TEXT columns."""
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return [part.strip() for part in str(raw).split(",") if part.strip()]
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def short_description(description: str, limit: int = 110) -> str:
    text = " ".join((description or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",.;") + "…"


def term_variants(term: str) -> list[str]:
    """A query word plus the singular forms it might be hiding.

    Without this a plural query silently under-counted: "what hoodies do you
    have" matched nothing, because "hoodies" is not a substring of "hoodie".
    English plurals are irregular enough that guessing one stem gets it wrong
    ("hoodies" is not "hoody"), so every plausible form is tried and a hit on
    any of them counts.
    """
    term = term.strip(" ,.?!\"'()")
    variants = [term]
    if len(term) > 3 and term.endswith("s") and not term.endswith("ss"):
        variants.append(term[:-1])                       # hoodies -> hoodie
        if term.endswith("es"):
            variants.append(term[:-2])                   # dresses -> dress
        if term.endswith("ies"):
            variants.append(term[:-3] + "y")             # parties -> party
    return [v for v in dict.fromkeys(variants) if len(v) > 1]


def sort_sizes(sizes: list[str]) -> list[str]:
    return sorted(sizes, key=lambda s: SIZE_ORDER.index(s) if s in SIZE_ORDER else len(SIZE_ORDER))


def stock_for(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = conn.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
    ).fetchall()
    sizes = [
        SizeStock(size=r["size"], quantity=int(r["quantity"]), in_stock=int(r["quantity"]) > 0)
        for r in rows
    ]
    sizes.sort(key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else len(SIZE_ORDER))
    return sizes


def stock_summary(name: str, in_stock: list[str], sold_out: list[str]) -> str:
    """A stock sentence built from the inventory rows, never from the model.

    The agent is told to repeat this rather than compose its own, which is what
    stops a sold-out size from being described as available.
    """
    if not in_stock:
        return f"{name} is sold out in every size right now."
    line = f"In stock in {', '.join(in_stock)}."
    if sold_out:
        line += f" Sold out in {', '.join(sold_out)}."
    return line


def to_card(row: sqlite3.Row, inventory: list[SizeStock]) -> ProductCard:
    in_stock = [s.size for s in inventory if s.quantity > 0]
    sold_out = [s.size for s in inventory if s.quantity == 0]
    return ProductCard(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        price=float(row["price"]),
        image_url=f"/images/{Path(row['image_file_path']).name}",
        short_description=short_description(row["description"]),
        colors=parse_json_list(row["colors"]),
        sizes_in_stock=in_stock,
        sold_out_sizes=sold_out,
        total_stock=sum(s.quantity for s in inventory),
        in_stock=bool(in_stock),
        stock_summary=stock_summary(row["name"], in_stock, sold_out),
    )


def to_detail(row: sqlite3.Row, inventory: list[SizeStock]) -> ProductDetail:
    card = to_card(row, inventory)
    return ProductDetail(
        **card.model_dump(),
        description=row["description"],
        search_tags=parse_json_list(row["search_tags"]),
        inventory=inventory,
    )


# ------------------------------------------------------------------ tools


def search_catalogue(
    query: str = "",
    garment_type: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    in_stock_only: bool = False,
    limit: int = 6,
) -> SearchResult:
    """Find products matching a shopper's description.

    `query` is matched across name, garment type, description, colors and
    search tags, so a college name, a sport or a graphic all work.

    Sold-out products are returned by default rather than hidden, so the agent
    can say "we carry that but it is sold out" instead of the misleading "we
    don't carry that". Each card's `in_stock` and `stock_summary` say which.
    """
    limit = max(1, min(int(limit), MAX_SEARCH_RESULTS))

    with closing(connect()) as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        inventories = {r["product_id"]: [] for r in rows}
        for r in conn.execute("SELECT product_id, size, quantity FROM inventory"):
            inventories.setdefault(r["product_id"], []).append(
                SizeStock(
                    size=r["size"],
                    quantity=int(r["quantity"]),
                    in_stock=int(r["quantity"]) > 0,
                )
            )

    scored: list[tuple[int, ProductCard]] = []
    terms = [term_variants(t) for t in query.lower().split()]
    terms = [v for v in terms if v]

    for row in rows:
        inventory = sorted(
            inventories.get(row["product_id"], []),
            key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else len(SIZE_ORDER),
        )
        card = to_card(row, inventory)

        if garment_type and not any(
            n in card.garment_type.lower() for n in expand_garment_type(garment_type)
        ):
            continue
        if color and not any(color.strip().lower() in c.lower() for c in card.colors):
            continue
        if max_price is not None and card.price > max_price:
            continue
        if in_stock_only and not card.in_stock:
            continue

        if not terms:
            scored.append((0, card))
            continue

        # Weight a name hit above a tag hit above a description hit, so
        # "saybrook crewneck" puts the Saybrook crewneck first.
        name = card.name.lower()
        tags = " ".join(parse_json_list(row["search_tags"])).lower()
        blob = f"{name} {card.garment_type.lower()} {row['description'].lower()} {tags} {' '.join(card.colors).lower()}"
        # A word scores on its best-matching variant: name beats tag beats
        # anywhere else, and a word is only counted once however many of its
        # forms hit.
        score = 0
        for variants in terms:
            if any(v in name for v in variants):
                score += 5
            elif any(v in tags for v in variants):
                score += 3
            elif any(v in blob for v in variants):
                score += 1
        if score:
            scored.append((score, card))

    # Relevance first, then in-stock, then price.
    #
    # Stock used to be the primary key, which pushed a product that is sold out
    # in every size past the result limit when enough in-stock products also
    # matched. Searching for that product by name then returned nothing, and
    # "we don't carry that" is the wrong answer for something the shop carries
    # but has sold out. Ranking by relevance first keeps a strong name match
    # visible; among equally relevant products, in-stock still comes first.
    scored.sort(key=lambda pair: (-pair[0], not pair[1].in_stock, pair[1].price))
    shown = [card for _, card in scored[:limit]]
    return SearchResult(
        query=query,
        count=len(scored),
        products=shown,
        sold_out_matches=sum(1 for _, card in scored if not card.in_stock),
        summary=search_summary(len(scored), len(shown)),
    )


def search_summary(total: int, shown: int) -> str:
    """How many matched and how many came back, written out.

    The agent repeats this instead of reporting a count itself — left to
    transcribe `count`, it reported the wrong number.
    """
    if total == 0:
        return "Nothing in the catalogue matches that."
    if total == shown:
        return f"{total} match{'' if total == 1 else 'es'}, all shown."
    return f"{total} matches; showing the first {shown}."


def get_product(product_id: str) -> ProductDetail | None:
    """Full detail for one product, including stock in every size."""
    with closing(connect()) as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return None
        return to_detail(row, stock_for(conn, product_id))


def check_size(product_id: str, size: str) -> SizeAvailability | None:
    """Whether one product is in stock in one size, and how many are left.

    Returns a ready-made `answer` sentence so the stock claim the shopper reads
    comes straight from the inventory row.
    """
    wanted = size.strip().upper()
    with closing(connect()) as conn:
        row = conn.execute(
            "SELECT product_id, name, price FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return None
        inventory = stock_for(conn, product_id)

    match = next((s for s in inventory if s.size.upper() == wanted), None)
    others = [s.size for s in inventory if s.quantity > 0 and s.size.upper() != wanted]
    sold_out = [s.size for s in inventory if s.quantity == 0]
    name = row["name"]

    if match is None:
        status = "size_not_carried"
        answer = f"{name} is not stocked in {wanted}."
    elif match.quantity > 0:
        status = "in_stock"
        unit = "one left" if match.quantity == 1 else f"{match.quantity} left"
        answer = f"{name} is in stock in {wanted} — {unit}."
    else:
        status = "out_of_stock"
        answer = f"{name} is sold out in {wanted}."

    if status != "in_stock":
        answer += (
            f" Available in {', '.join(others)}." if others else " It is sold out in every size."
        )

    return SizeAvailability(
        product_id=row["product_id"],
        name=name,
        size=wanted,
        status=status,
        available=bool(match and match.quantity > 0),
        quantity=match.quantity if match else 0,
        price=float(row["price"]),
        other_sizes_in_stock=others,
        sold_out_sizes=sold_out,
        answer=answer,
    )


def list_categories() -> list[CategorySummary]:
    """The garment categories the shop groups its stock into, with counts."""
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT garment_type, COUNT(*) AS n FROM catalogue GROUP BY garment_type"
        ).fetchall()

    summaries = []
    for label, needles in CATEGORIES:
        count = sum(r["n"] for r in rows if any(n in r["garment_type"].lower() for n in needles))
        if count:
            summaries.append(CategorySummary(label=label, match=",".join(needles), count=count))
    return summaries


def price_range(garment_type: str | None = None) -> PriceRange:
    """What the shop charges, overall or within one category."""
    with closing(connect()) as conn:
        rows = conn.execute("SELECT garment_type, price FROM catalogue").fetchall()

    needles = expand_garment_type(garment_type) if garment_type else []
    prices = [
        float(r["price"])
        for r in rows
        if not needles or any(n in r["garment_type"].lower() for n in needles)
    ]
    if not prices:
        return PriceRange(lowest=0, highest=0, average=0, count=0, garment_type=garment_type)
    return PriceRange(
        lowest=min(prices),
        highest=max(prices),
        average=round(sum(prices) / len(prices), 2),
        count=len(prices),
        garment_type=garment_type,
    )


# ---------------------------------------------------------------------------
# Chat history
#
# Signed-in customers get their conversation kept in the existing
# `chat_messages` table, keyed by `user_id`. Guests are never written to it.
# ---------------------------------------------------------------------------

# How many stored turns to reload. Enough to feel remembered, bounded so a long
# history cannot grow the prompt without limit.
HISTORY_LIMIT = 40


def load_history(user_id: int, limit: int = HISTORY_LIMIT) -> list[ChatMessage]:
    """Read a customer's saved conversation back, oldest turn first."""
    with closing(connect()) as conn:
        rows = conn.execute(
            """SELECT role, content, products_json, created_at
                 FROM chat_messages
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?""",
            (user_id, limit),
        ).fetchall()

    messages: list[ChatMessage] = []
    for row in reversed(rows):
        messages.append(
            ChatMessage(
                role=row["role"],
                content=row["content"],
                products=parse_products_json(row["products_json"]),
                created_at=row["created_at"],
            )
        )
    return messages


def parse_products_json(raw: Any) -> list[ProductCard]:
    """Rebuild the product cards stored alongside an assistant turn.

    Some seeded rows hold the literal string "None" rather than SQL NULL, and
    older rows may not carry every field the card has now, so anything that
    does not validate is dropped rather than breaking the reload.
    """
    if not raw or raw in ("None", "null"):
        return []
    try:
        items = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(items, list):
        return []

    cards: list[ProductCard] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            cards.append(ProductCard.model_validate(item))
        except ValidationError:
            # A stored card from an older schema: keep what we can.
            try:
                cards.append(
                    ProductCard(
                        product_id=item["product_id"],
                        name=item.get("name", item["product_id"]),
                        garment_type=item.get("garment_type", ""),
                        price=float(item.get("price", 0) or 0),
                        image_url=item.get("image_url")
                        or f"/images/{item['product_id']}.jpg",
                        short_description=item.get("short_description", ""),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
    return cards


def save_turn(
    user_id: int,
    role: str,
    content: str,
    products: list[ProductCard] | None = None,
) -> None:
    """Append one turn to a signed-in customer's history."""
    products_json = (
        json.dumps([p.model_dump(mode="json") for p in products]) if products else None
    )
    with closing(connect()) as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, ?, ?, ?)",
            (user_id, role, content, products_json),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Batch helpers
# ---------------------------------------------------------------------------


def cards_for(product_ids: list[str]) -> list[ProductCard]:
    """Expand product ids into full cards, in the order given.

    One query for the catalogue rows and one for the inventory, rather than a
    pair per product. Unknown ids are skipped.
    """
    wanted = [pid for pid in dict.fromkeys(product_ids) if pid]
    if not wanted:
        return []

    placeholders = ",".join("?" * len(wanted))
    with closing(connect()) as conn:
        rows = {
            r["product_id"]: r
            for r in conn.execute(
                f"SELECT * FROM catalogue WHERE product_id IN ({placeholders})", wanted
            )
        }
        stock: dict[str, list[SizeStock]] = {}
        for r in conn.execute(
            f"SELECT product_id, size, quantity FROM inventory WHERE product_id IN ({placeholders})",
            wanted,
        ):
            stock.setdefault(r["product_id"], []).append(
                SizeStock(
                    size=r["size"], quantity=int(r["quantity"]), in_stock=int(r["quantity"]) > 0
                )
            )

    cards = []
    for pid in wanted:
        row = rows.get(pid)
        if row is None:
            continue
        inventory = sorted(
            stock.get(pid, []),
            key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else len(SIZE_ORDER),
        )
        cards.append(to_card(row, inventory))
    return cards


def find_in_size(
    size: str,
    garment_type: str | None = None,
    max_price: float | None = None,
    limit: int = 6,
) -> SizeSearchResult:
    """Everything buyable in one size, in a single query.

    Answering "what do you have in XXL?" by searching and then checking each
    result costs one tool call per product. This does it in one.
    """
    wanted = size.strip().upper()
    limit = max(1, min(int(limit), MAX_SEARCH_RESULTS))
    needles = expand_garment_type(garment_type) if garment_type else []

    with closing(connect()) as conn:
        rows = conn.execute(
            """SELECT c.*, i.quantity
                 FROM catalogue c
                 JOIN inventory i ON i.product_id = c.product_id
                WHERE UPPER(i.size) = ? AND i.quantity > 0
                ORDER BY c.price, c.name""",
            (wanted,),
        ).fetchall()

    matches = [
        r
        for r in rows
        if (not needles or any(n in r["garment_type"].lower() for n in needles))
        and (max_price is None or float(r["price"]) <= max_price)
    ]
    cards = cards_for([r["product_id"] for r in matches[:limit]])

    if not matches:
        summary = f"Nothing is in stock in {wanted}" + (
            f" in that category." if needles else " right now."
        )
    elif len(matches) <= limit:
        summary = f"{len(matches)} in stock in {wanted}, all shown."
    else:
        summary = f"{len(matches)} in stock in {wanted}; showing the first {len(cards)}."

    return SizeSearchResult(
        size=wanted, count=len(matches), products=cards, summary=summary
    )
