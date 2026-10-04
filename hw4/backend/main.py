"""Campus Customs backend.

The FastAPI app behind the Campus Customs website. It serves the catalogue,
per-size inventory and product images from the SQLite database, handles
accounts and sessions, and passes chat messages to the PydanticAI agent.

Run it from this folder:

    uvicorn main:app --reload --port 8000

Layout:
    agent.py    the PydanticAI agent: model, system prompt, tool wiring
    tools.py    the catalogue lookups the agent calls, shared with the API
    models.py   Pydantic types for chat replies and product cards
    auth.py     password hashing and signed session cookies
    prompts/    the agent's system prompt
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from fastapi import Cookie, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

import agent as chat_agent
from auth import (
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    hash_password,
    issue_session,
    read_session,
    verify_password,
)
from models import ChatHistory, ChatMessage, ChatReply, ChatRequest, CustomerContext
# The catalogue helpers live in tools.py so the agent and these endpoints read
# the database exactly the same way and can never disagree about stock.
from tools import (
    DB_PATH,
    SIZE_ORDER,
    connect,
    load_history,
    parse_json_list,
    save_turn,
    short_description,
)

logger = logging.getLogger("campus_customs")

# Set CAMPUS_CUSTOMS_HTTPS=1 when the site is served over HTTPS so the session
# cookie is marked Secure and never travels over plain HTTP. Off by default
# because the course app runs on http://localhost.
COOKIE_SECURE = os.environ.get("CAMPUS_CUSTOMS_HTTPS", "").lower() in {"1", "true", "yes"}

HW4_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = HW4_DIR / "data"
IMAGES_DIR = DATA_DIR / "products"

app = FastAPI(
    title="Campus Customs API",
    description="Catalogue, inventory, product images, accounts, and the shopping-assistant chat.",
    version="0.2.0",
)

# The Vite dev server runs on a different port, so the browser needs CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5180", "http://127.0.0.1:5180"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FastAPI's default validation error echoes the rejected value back to the
# client, which would put a submitted password in the response body. Redact any
# field whose name looks like a secret before the error leaves the server.
SECRET_FIELDS = {"password", "confirm_password"}


@app.exception_handler(RequestValidationError)
async def redact_validation_errors(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for error in exc.errors():
        cleaned = {k: v for k, v in error.items() if k != "input"}
        # `ctx` can hold the original exception object, which is not JSON
        # serializable and would turn a 422 into a 500.
        if "ctx" in cleaned:
            cleaned["ctx"] = {k: str(v) for k, v in cleaned["ctx"].items()}
        if any(part in SECRET_FIELDS for part in error.get("loc", ())):
            # The value is gone either way; the message still has to describe
            # the actual problem rather than always blaming the length.
            kind = error.get("type", "")
            if kind == "missing":
                cleaned["msg"] = "Password is required."
            elif kind == "string_too_long":
                cleaned["msg"] = "That password is too long."
            else:
                cleaned["msg"] = "Your password must be at least 8 characters."
            cleaned.pop("ctx", None)
        errors.append(cleaned)
    return JSONResponse(status_code=422, content={"detail": errors})


if IMAGES_DIR.is_dir():
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


def image_url(image_file_path: str) -> str:
    """`products/foo.jpg` in the DB maps to the mounted `/images/foo.jpg`."""
    return f"/images/{Path(image_file_path).name}"


def row_to_product(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "short_description": short_description(row["description"]),
        "colors": parse_json_list(row["colors"]),
        "search_tags": parse_json_list(row["search_tags"]),
        "image_url": image_url(row["image_file_path"]),
        "price": float(row["price"]),
    }


def fetch_inventory(conn: sqlite3.Connection, product_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
    ).fetchall()
    sizes = [{"size": r["size"], "quantity": int(r["quantity"])} for r in rows]
    sizes.sort(
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else len(SIZE_ORDER)
    )
    return sizes


@app.get("/api/health")
def health() -> dict[str, Any]:
    with closing(connect()) as conn:
        products = conn.execute("SELECT COUNT(*) FROM catalogue").fetchone()[0]
    return {"status": "ok", "database": str(DB_PATH), "products": products}


@app.get("/api/products")
def list_products(
    search: str | None = Query(default=None, description="Free-text match on name, type, description, colors, or tags"),
    garment_type: str | None = Query(default=None, description="Comma-separated case-insensitive substrings, e.g. 'jacket,fleece'"),
    in_stock_only: bool = Query(default=False, description="Only products with at least one size in stock"),
) -> dict[str, Any]:
    """The catalogue, optionally filtered. Each product carries a stock summary."""
    with closing(connect()) as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        products = [row_to_product(r) for r in rows]

        # One pass over inventory instead of a query per product.
        totals: dict[str, int] = {}
        available: dict[str, list[str]] = {}
        for r in conn.execute("SELECT product_id, size, quantity FROM inventory"):
            totals[r["product_id"]] = totals.get(r["product_id"], 0) + int(r["quantity"])
            if int(r["quantity"]) > 0:
                available.setdefault(r["product_id"], []).append(r["size"])

    for product in products:
        pid = product["product_id"]
        sizes = available.get(pid, [])
        sizes.sort(key=lambda s: SIZE_ORDER.index(s) if s in SIZE_ORDER else len(SIZE_ORDER))
        product["total_stock"] = totals.get(pid, 0)
        product["sizes_in_stock"] = sizes

    # `garment_type` is not normalized in the DB ("short-sleeve t-shirt" vs
    # "short-sleeve T-shirt", "hoodie" vs "pullover hoodie"), so match loosely
    # against a comma-separated list of substrings.
    if garment_type:
        needles = [n.strip().lower() for n in garment_type.split(",") if n.strip()]
        products = [
            p for p in products if any(n in p["garment_type"].lower() for n in needles)
        ]

    if search:
        needle = search.strip().lower()
        def matches(p: dict[str, Any]) -> bool:
            haystack = " ".join(
                [p["name"], p["garment_type"], p["description"], *p["colors"], *p["search_tags"]]
            ).lower()
            return needle in haystack
        products = [p for p in products if matches(p)]

    if in_stock_only:
        products = [p for p in products if p["sizes_in_stock"]]

    return {"count": len(products), "products": products}


@app.get("/api/garment-types")
def garment_types() -> dict[str, Any]:
    """Collapsed categories for the Products page filter bar.

    The raw `garment_type` values are inconsistent, so group them into the
    handful of categories a shopper actually asks for.
    """
    # Each needle list is passed straight back as the `match` query value, so a
    # category's count always equals what /api/products returns for that chip.
    groups = [
        ("Hoodies", ["hood"]),
        ("Crewnecks", ["crewneck", "mockneck"]),
        ("T-shirts", ["t-shirt"]),
        ("Quarter-zips", ["quarter-zip"]),
        ("Jackets & fleece", ["jacket", "fleece"]),
        ("Performance", ["performance"]),
    ]
    with closing(connect()) as conn:
        rows = conn.execute("SELECT garment_type, COUNT(*) AS n FROM catalogue GROUP BY garment_type").fetchall()

    result = []
    for label, needles in groups:
        count = sum(
            r["n"] for r in rows if any(n in r["garment_type"].lower() for n in needles)
        )
        if count:
            result.append({"label": label, "match": ",".join(needles), "count": count})
    return {"categories": result}


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict[str, Any]:
    """Full product detail, including per-size stock."""
    with closing(connect()) as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"No product with id '{product_id}'")
        product = row_to_product(row)
        product["inventory"] = fetch_inventory(conn, product_id)

    product["total_stock"] = sum(s["quantity"] for s in product["inventory"])
    product["sizes_in_stock"] = [s["size"] for s in product["inventory"] if s["quantity"] > 0]
    return product


@app.get("/api/products/{product_id}/inventory")
def get_inventory(product_id: str) -> dict[str, Any]:
    """Per-size stock on its own, for the size picker."""
    with closing(connect()) as conn:
        exists = conn.execute(
            "SELECT 1 FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail=f"No product with id '{product_id}'")
        sizes = fetch_inventory(conn, product_id)

    return {
        "product_id": product_id,
        "inventory": sizes,
        "total_stock": sum(s["quantity"] for s in sizes),
    }


# ---------------------------------------------------------------------------
# Accounts
#
# Passwords only ever exist here as PBKDF2 digests (see auth.py). No endpoint
# returns `password_hash`, and the plaintext password is not logged or stored.
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    confirm_password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def public_user(row: sqlite3.Row) -> dict[str, Any]:
    """The only shape a user is ever returned in — note the absent hash."""
    return {
        "id": row["id"],
        "name": row["name"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "email": row["email"],
        "created_at": row["created_at"],
    }


def set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        issue_session(user_id),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,   # unreadable from JavaScript
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def current_user(conn: sqlite3.Connection, token: str | None) -> sqlite3.Row | None:
    user_id = read_session(token)
    if user_id is None:
        return None
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


@app.post("/api/auth/register", status_code=201)
def register(payload: RegisterRequest, response: Response) -> dict[str, Any]:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Those passwords do not match.")

    email = payload.email.strip().lower()
    first = payload.first_name.strip()
    last = payload.last_name.strip()

    with closing(connect()) as conn:
        taken = conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone()
        if taken:
            raise HTTPException(status_code=409, detail="An account with that email already exists.")

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name)"
            " VALUES (?, ?, ?, ?, ?)",
            (f"{first} {last}", email, hash_password(payload.password), first, last),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()

    set_session_cookie(response, row["id"])
    return {"user": public_user(row)}


@app.post("/api/auth/login")
def login(payload: LoginRequest, response: Response) -> dict[str, Any]:
    email = payload.email.strip().lower()
    with closing(connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()

    # Same message and same work either way, so a wrong email cannot be told
    # apart from a wrong password.
    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="That email and password do not match.")

    set_session_cookie(response, row["id"])
    return {"user": public_user(row)}


@app.post("/api/auth/logout")
def logout(response: Response) -> dict[str, Any]:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, secure=COOKIE_SECURE, samesite="lax")
    return {"ok": True}


@app.get("/api/auth/me")
def me(cc_session: str | None = Cookie(default=None)) -> dict[str, Any]:
    """Who the browser is signed in as, or `null` when signed out."""
    with closing(connect()) as conn:
        row = current_user(conn, cc_session)
    return {"user": public_user(row) if row else None}


# ---------------------------------------------------------------------------
# Chat
#
# The website's chat widget posts here; the PydanticAI agent in agent.py
# answers. The agent's reply is validated against `ChatReply` before it is
# returned, so the frontend always gets a message plus real product cards.
# ---------------------------------------------------------------------------


def customer_context(row: sqlite3.Row | None) -> CustomerContext:
    """Who the agent is told it is talking to.

    Built from the session cookie, never from the request body, so the
    identity cannot be spoofed by the browser or talked into changing.
    """
    if row is None:
        return CustomerContext(signed_in=False)
    return CustomerContext(
        signed_in=True,
        user_id=row["id"],
        name=row["name"],
        first_name=row["first_name"] or row["name"].split(" ")[0],
        email=row["email"],
    )


@app.get("/api/chat/history", response_model=ChatHistory)
def chat_history(cc_session: str | None = Cookie(default=None)) -> ChatHistory:
    """A signed-in customer's saved conversation; empty for a guest."""
    with closing(connect()) as conn:
        user = current_user(conn, cc_session)
    if user is None:
        return ChatHistory(signed_in=False, messages=[])
    return ChatHistory(signed_in=True, messages=load_history(user["id"]))


@app.post("/api/chat", response_model=ChatReply)
async def chat(
    payload: ChatRequest, cc_session: str | None = Cookie(default=None)
) -> ChatReply:
    """Send one message to the Campus Customs agent and return its reply.

    Signed-in customers get their history read from and written back to
    `chat_messages`. Guests can chat just the same, but nothing is stored —
    their thread lives only in the browser tab.
    """
    with closing(connect()) as conn:
        user = current_user(conn, cc_session)
    customer = customer_context(user)

    # A signed-in customer's history comes from the database, not the request,
    # so it survives logging out and coming back on another day or device.
    history: list[ChatMessage] = (
        load_history(user["id"]) if user is not None else payload.history
    )

    try:
        reply = await chat_agent.answer(
            payload.message, history, customer=customer, page=payload.page
        )
    except Exception:
        # Log the cause for the developer, but never leak provider errors —
        # they can carry request URLs or key fragments — to the browser.
        logger.exception("Chat agent failed")
        raise HTTPException(
            status_code=502,
            detail="The shopping assistant is unavailable right now. Please try again.",
        )

    if user is not None:
        # Written only after a successful answer, so a failed turn does not
        # leave a question in the history with no reply.
        save_turn(user["id"], "user", payload.message)
        save_turn(user["id"], "assistant", reply.message, reply.products)

    return reply


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
