"""Structured types shared by the API and the PydanticAI agent.

`ChatReply` is the agent's output type, so PydanticAI validates the model's
answer against it before it ever reaches the website.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------- catalogue


StockStatus = Literal["in_stock", "out_of_stock"]


class SizeStock(BaseModel):
    """How many units of one size of one product are on the shelf."""

    size: str = Field(description="XS, S, M, L, XL or XXL")
    quantity: int = Field(ge=0, description="Units in stock; 0 means sold out")
    in_stock: bool = Field(
        description="False when quantity is 0. Say so plainly rather than offering the size."
    )


class ProductCard(BaseModel):
    """One product, in the shape the website renders as a card.

    Everything here comes from the catalogue; the agent fills it from tool
    results rather than from memory.
    """

    product_id: str
    name: str
    garment_type: str
    price: float = Field(ge=0)
    image_url: str = Field(description="Served by the backend, e.g. /images/foo.jpg")
    short_description: str = ""
    colors: list[str] = Field(default_factory=list)
    sizes_in_stock: list[str] = Field(
        default_factory=list, description="Sizes with quantity > 0 — the only sizes that can be sold"
    )
    sold_out_sizes: list[str] = Field(
        default_factory=list, description="Sizes stocked but currently at 0. Name these as sold out."
    )
    total_stock: int = Field(default=0, ge=0, description="Units across every size")
    in_stock: bool = Field(
        default=False, description="False when every size is 0. Tell the shopper it is sold out."
    )
    stock_summary: str = Field(
        default="",
        description="Plain-language stock line built from the database, e.g. 'Sold out in S'. "
        "Repeat this rather than composing your own stock claim.",
    )


class ProductDetail(ProductCard):
    """A product card plus the full description and per-size stock."""

    description: str = ""
    search_tags: list[str] = Field(default_factory=list)
    inventory: list[SizeStock] = Field(default_factory=list)


# ------------------------------------------------------------ tool results


class SearchResult(BaseModel):
    """What `search_catalogue` hands back to the agent."""

    query: str
    count: int = Field(ge=0, description="Total matches before the result limit was applied")
    products: list[ProductCard]
    sold_out_matches: int = Field(
        default=0, ge=0, description="Matches with no size in stock — mention these as sold out."
    )
    summary: str = Field(
        default="",
        description="How many matched and how many are shown, already phrased. Use this wording "
        "rather than counting the cards or recalling a number.",
    )


class SizeAvailability(BaseModel):
    """What `check_size` hands back to the agent.

    `answer` is the sentence to give the shopper. It is built from the database
    row, so repeating it is what keeps a stock claim from being invented.
    """

    product_id: str
    name: str
    size: str
    status: StockStatus | Literal["size_not_carried"] = Field(
        description="in_stock, out_of_stock, or size_not_carried if the shop never stocks that size"
    )
    available: bool = Field(description="True only when quantity > 0")
    quantity: int = Field(ge=0, description="Units left in this size; 0 means sold out")
    price: float = Field(default=0.0, ge=0)
    other_sizes_in_stock: list[str] = Field(
        default_factory=list, description="Sizes you can offer instead when this one is sold out"
    )
    sold_out_sizes: list[str] = Field(default_factory=list)
    answer: str = Field(
        default="", description="The stock sentence, already phrased. Say this, do not rewrite it."
    )


class SizeSearchResult(BaseModel):
    """What `find_in_size` hands back: everything buyable in one size."""

    size: str
    count: int = Field(ge=0, description="How many products are in stock in this size")
    products: list[ProductCard] = Field(default_factory=list)
    summary: str = Field(default="", description="Already phrased; say this rather than counting")


class CategorySummary(BaseModel):
    label: str
    match: str
    count: int


class PriceRange(BaseModel):
    """What `price_range` hands back. Every figure is computed from the catalogue."""

    lowest: float = Field(ge=0)
    highest: float = Field(ge=0)
    average: float = Field(ge=0)
    count: int = Field(ge=0, description="How many products these figures cover")
    garment_type: str | None = Field(
        default=None, description="The category these figures cover, or None for the whole shop"
    )


# -------------------------------------------------------------- chat shapes


class ChatMessage(BaseModel):
    """One turn of conversation, as it is stored, replayed and sent back."""

    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(
        default_factory=list,
        description="Products the assistant showed on this turn, so reloaded history redraws them",
    )
    created_at: str | None = None


class CustomerContext(BaseModel):
    """Who the agent is talking to.

    Built on the server from the session cookie — never from anything the
    browser sends — so a visitor cannot claim to be someone else.
    """

    signed_in: bool = False
    user_id: int | None = None
    name: str | None = None
    first_name: str | None = None
    email: str | None = None


class PageContext(BaseModel):
    """What the customer is looking at while they type.

    `product_id` is what makes "do you have this in pink?" answerable: the
    backend resolves it against the catalogue before the agent runs.
    """

    path: str | None = Field(default=None, description="e.g. /products/basic-hoodie-big-yale")
    product_id: str | None = Field(default=None, description="Set when a product page is open")
    category: str | None = Field(default=None, description="Category filter on the Products page")


class AgentReply(BaseModel):
    """What the model is asked to produce.

    It returns product *ids*, not whole product records. Re-emitting six full
    cards costs roughly 800 output tokens per answer and risks the model
    altering a price or a size list on the way through; six ids cost about 45
    and cannot drift. The backend expands them from the catalogue.
    """

    message: str = Field(
        description="What to say to the shopper. Two or three sentences, no re-listing the cards."
    )
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=8,
        description="product_id of each product to show, in the order they should appear. "
        "Copy them exactly from the tool results.",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Up to three short follow-up questions the shopper might tap next.",
    )


class ChatReply(BaseModel):
    """The API's chat response body.

    Keeping `products` separate from `message` is what lets the site draw real
    product cards instead of parsing names out of prose. The cards are built by
    the backend from the ids the agent returned, so every field is straight
    from the catalogue.
    """

    message: str
    products: list[ProductCard] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """A message from the website chat widget."""

    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        """A message of only spaces passed `min_length` and cost a model call."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Type a message first.")
        return cleaned
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Earlier turns for a guest. Ignored for signed-in users, whose history "
        "is read from the database instead.",
    )
    page: PageContext | None = Field(
        default=None, description="What the customer is looking at right now"
    )


class ChatHistory(BaseModel):
    """What `GET /api/chat/history` returns when a customer comes back."""

    signed_in: bool
    messages: list[ChatMessage] = Field(default_factory=list)
