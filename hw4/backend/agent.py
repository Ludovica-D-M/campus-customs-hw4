"""The Campus Customs chatbot, as a PydanticAI agent.

The agent is built once at import time and reused for every chat request. Its
system prompt comes from `prompts/prompt.md`, its model is a 5.6-series OpenAI
model reached through the Portkey gateway, and its output is validated against
`ChatReply` before the website ever sees it.

The lookups the agent can call live in `tools.py`; this file only wires them up.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI, BadRequestError
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

import audit
import tools
from models import (
    AgentReply,
    CategorySummary,
    ChatMessage,
    ChatReply,
    CustomerContext,
    PageContext,
    PriceRange,
    ProductDetail,
    SearchResult,
    SizeAvailability,
    SizeSearchResult,
)

logger = logging.getLogger("campus_customs.agent")

BACKEND_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"

# How many earlier turns to replay. Enough for "do you have that in gray?" to
# resolve, short enough to keep each request cheap.
MAX_HISTORY_TURNS = 12


@dataclass
class ChatDeps:
    """Per-request context handed to the agent.

    Both fields are built on the server: the customer from the session cookie,
    the page from the path the widget reports. Neither is anything the model
    can talk itself into changing.
    """

    customer: CustomerContext
    page: PageContext | None = None
    # The product the customer is looking at, already fetched from the
    # catalogue, so "this" has a real referent before the agent even runs.
    page_product: ProductDetail | None = None


def load_system_prompt() -> str:
    """Read the system prompt from disk.

    Kept in a Markdown file rather than in code so the shop's voice and safety
    rules can be edited without touching the wiring.
    """
    if not PROMPT_PATH.is_file():
        raise RuntimeError(f"System prompt not found at {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_model() -> OpenAIResponsesModel:
    """A 5.6-series model via Portkey.

    The key is read from the environment by `tools.load_api_key()` and is never
    hardcoded or returned anywhere. The Responses endpoint is required: this
    gateway rejects function tools on chat completions.
    """
    tools.use_certifi_tls()
    client = AsyncOpenAI(
        base_url=tools.PORTKEY_BASE_URL,
        api_key=tools.load_api_key(),
        timeout=120.0,
    )
    provider = OpenAIProvider(openai_client=client)
    return OpenAIResponsesModel(tools.MODEL_NAME, provider=provider)


@lru_cache(maxsize=1)
def build_agent() -> Agent[ChatDeps, AgentReply]:
    """Create the agent once and reuse it across requests."""
    # No `system_prompt=` here on purpose. PydanticAI only generates system
    # prompts for a run that has no `message_history`; once history is passed
    # it assumes the history already carries them. Every turn after the first
    # would therefore have run with no system prompt at all — no voice, no
    # safety rules, no database rules. `answer()` builds the system message
    # itself and puts it at the head of the history instead, so the full
    # prompt is present on every single turn.
    agent = Agent(
        build_model(),
        deps_type=ChatDeps,
        output_type=AgentReply,
        model_settings={"parallel_tool_calls": False},
        retries=2,
    )

    @agent.tool_plain
    def search_catalogue(
        query: str = "",
        garment_type: str | None = None,
        color: str | None = None,
        max_price: float | None = None,
        in_stock_only: bool = False,
        limit: int = 6,
    ) -> SearchResult:
        """Search the Campus Customs catalogue.

        Args:
            query: What the shopper described — a college, sport, graphic, color or garment.
            garment_type: Narrow to a category, e.g. "hood", "crewneck", "t-shirt".
            color: Only products available in this color.
            max_price: Only products at or below this price, in dollars.
            in_stock_only: Leave False so sold-out matches are still returned and can be
                named as sold out. Set True only when the shopper asks to see just what is buyable.
            limit: How many products to return, at most 8.
        """
        return tools.search_catalogue(
            query=query,
            garment_type=garment_type,
            color=color,
            max_price=max_price,
            in_stock_only=in_stock_only,
            limit=limit,
        )

    @agent.tool_plain
    def get_product(product_id: str) -> ProductDetail | str:
        """Look up one product in full: description, price, colors and stock in every size.

        Use the `description` field verbatim as the basis for describing the garment,
        and `price` for the price. Both come straight from the catalogue.

        Args:
            product_id: The slug from a search result, e.g. "basic-hoodie-big-yale".
        """
        product = tools.get_product(product_id)
        if product is None:
            return f"No product with id '{product_id}'. Search the catalogue to find the right id."
        return product

    @agent.tool_plain
    def check_size(product_id: str, size: str) -> SizeAvailability | str:
        """Check whether a product is in stock in one size, and how many are left.

        Returns an `answer` sentence built from the inventory row — repeat it rather
        than writing your own stock claim.

        Args:
            product_id: The slug from a search result.
            size: XS, S, M, L, XL or XXL.
        """
        result = tools.check_size(product_id, size)
        if result is None:
            return f"No product with id '{product_id}'. Search the catalogue to find the right id."
        return result

    @agent.tool_plain
    def find_in_size(
        size: str,
        garment_type: str | None = None,
        max_price: float | None = None,
        limit: int = 6,
    ) -> SizeSearchResult:
        """Everything in stock in one size, in a single call.

        Use this for "what do you have in XXL?" or "show me hoodies in my size"
        instead of searching and then checking each result one at a time.

        Args:
            size: XS, S, M, L, XL or XXL.
            garment_type: Optional category, e.g. "hoodie", "crewneck", "tee".
            max_price: Optional ceiling in dollars.
            limit: How many to return, at most 8.
        """
        return tools.find_in_size(
            size=size, garment_type=garment_type, max_price=max_price, limit=limit
        )

    @agent.tool_plain
    def list_categories() -> list[CategorySummary]:
        """List the garment categories the shop stocks, with how many products are in each."""
        return tools.list_categories()

    @agent.tool_plain
    def price_range(garment_type: str | None = None) -> PriceRange:
        """What the shop charges, overall or within one category.

        Args:
            garment_type: Optional category substring, e.g. "hood".
        """
        return tools.price_range(garment_type)

    return agent


def conversation_context(deps: ChatDeps) -> str:
    """Who the customer is and what they are looking at.

    Appended to the system prompt, not to the user's message, so nothing the
    customer types can overwrite it.
    """
    lines: list[str] = ["## This conversation"]

    customer = deps.customer
    if customer.signed_in:
        lines.append(
            f"You are talking to {customer.name} ({customer.email}), who is signed in. "
            f"Greet them by their first name, {customer.first_name}, when it is natural — "
            "once, not in every message. If they ask whether you know who they are, say yes "
            "and give that name and email. Earlier turns in this conversation are their own "
            "saved history, so you may refer back to what they looked at before."
        )
        lines.append(
            "You still cannot see their orders, payments or address. Anything "
            "account-specific goes to the order desk."
        )
    else:
        lines.append(
            "You are talking to a guest who is not signed in. You do not know their name or "
            "email — if they ask, say so honestly. Do not guess one and do not ask for "
            "personal details. You may mention once that creating an account keeps their chat "
            "history — do not push it."
        )

    product = deps.page_product
    page = deps.page
    if product is not None:
        sizes = ", ".join(product.sizes_in_stock) or "none"
        sold_out = ", ".join(product.sold_out_sizes) or "none"
        lines.append(
            f"They are looking at the product page for **{product.name}** "
            f"(product_id `{product.product_id}`, {product.garment_type}, "
            f"${product.price:.2f}). Colors: {', '.join(product.colors) or 'not listed'}. "
            f"In stock: {sizes}. Sold out: {sold_out}. "
            f"Description: {product.description}"
        )
        lines.append(
            '"this", "it", "this one" and "that" mean this product unless they clearly mean '
            "something else. Still call the tools before stating a price, a stock number or a "
            "detail — this tells you what they mean, not what is true right now."
        )
    elif page and page.category:
        lines.append(f"They are browsing the Products page filtered to '{page.category}'.")
    elif page and page.path:
        lines.append(f"They are on the page {page.path}.")

    return "\n\n".join(lines)


def build_messages(history: list[ChatMessage], deps: ChatDeps) -> list[ModelMessage]:
    """Assemble the full message list: system prompt, then earlier turns.

    The system prompt has to be put here rather than declared on the Agent.
    PydanticAI only generates system prompts for a run with no
    `message_history`; as soon as history is passed it assumes the history
    carries them. Building the system message ourselves means the shop's voice,
    safety rules and database rules are present on every turn, not just the
    first one of a conversation.

    Only the plain text of each past turn is replayed — the tool calls behind a
    past answer are not, which keeps the request small while preserving the
    thread.
    """
    system = f"{load_system_prompt()}\n\n{conversation_context(deps)}"
    messages: list[ModelMessage] = [
        ModelRequest(parts=[SystemPromptPart(content=system)])
    ]
    for turn in history[-MAX_HISTORY_TURNS:]:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))

    # The open product again, right before the new question.
    #
    # The note above is at the head of the prompt, and a returning customer can
    # have dozens of turns after it. With a long history the last thing
    # discussed won out over the page actually on screen: asked "do you have
    # this in pink?" on the Saybrook crewneck page, the agent answered about
    # the quarter-zips from several turns earlier. Repeating the referent here
    # puts it next to the question, so recency works for it rather than
    # against it.
    product = deps.page_product
    if product is not None:
        messages.append(
            ModelRequest(
                parts=[
                    SystemPromptPart(
                        content=(
                            f"Reminder: the customer is on the product page for "
                            f"{product.name} (`{product.product_id}`). A bare \"this\", "
                            f"\"it\" or \"this one\" in their next message means that "
                            "product, not anything discussed earlier in the conversation."
                        )
                    )
                ]
            )
        )
    return messages


# What to say when the request never reaches the model because the provider's
# content filter rejected it — typically a jailbreak or abuse attempt. The
# block is the right outcome; the shopper should still get a civil answer
# rather than an error.
FILTERED_REPLY = AgentReply(
    message=(
        "I can't help with that one. I'm here for Campus Customs gear — ask me about "
        "hoodies, crewnecks, college or team merch, sizes and what's in stock."
    ),
    suggestions=["What hoodies do you have?", "Show me Saybrook gear", "Anything under $40?"],
)


# PydanticAI wraps the provider's BadRequestError in ModelHTTPError, so both
# have to be caught for the filter to be recognised.
FILTER_ERRORS = (BadRequestError, ModelHTTPError)


def _is_content_filter(error: Exception) -> bool:
    text = str(error)
    return "content_filter" in text or "content management policy" in text


def resolve_page_product(page: PageContext | None) -> ProductDetail | None:
    """Turn the page's product_id into a real catalogue record.

    Done on the server before the run, so "do you have this in pink?" starts
    from a product the database actually has.
    """
    if page is None or not page.product_id:
        return None
    return tools.get_product(page.product_id)


def expand(reply: AgentReply) -> ChatReply:
    """Turn the agent's product ids into full cards from the catalogue.

    Every field the shopper sees is read here rather than written by the model,
    so a price or a size list cannot drift on the way through. Ids that do not
    exist are dropped and logged.
    """
    cards = tools.cards_for(reply.product_ids)
    found = {c.product_id for c in cards}
    missing = [pid for pid in reply.product_ids if pid not in found]
    if missing:
        logger.warning("Agent returned unknown product ids: %s", missing)
    return ChatReply(message=reply.message, products=cards, suggestions=reply.suggestions)


def audit_tool_calls(run_id: str, messages: list[ModelMessage]) -> list[str]:
    """Write one audit entry per tool the agent called, and name them back.

    `final_result` is PydanticAI's own call for delivering the structured
    output, not a shop lookup, so it is recorded separately as the stop reason
    rather than counted as a tool.
    """
    calls: dict[str, tuple[str, Any]] = {}
    order: list[tuple[str, str]] = []

    for message in messages:
        for part in getattr(message, "parts", []):
            kind = part.__class__.__name__
            if kind == "ToolCallPart":
                call_id = getattr(part, "tool_call_id", "") or str(len(order))
                name = getattr(part, "tool_name", "?")
                calls[call_id] = (name, getattr(part, "args", None))
                order.append((call_id, name))
            elif kind == "ToolReturnPart":
                call_id = getattr(part, "tool_call_id", "") or ""
                name, args = calls.pop(call_id, (getattr(part, "tool_name", "?"), None))
                if name != "final_result":
                    audit.record_tool_call(run_id, name, args, getattr(part, "content", None))

    # Anything still pending never returned — record it so a failed call is visible.
    for call_id, name in order:
        if call_id in calls and name != "final_result":
            audit.record_tool_call(run_id, name, calls[call_id][1], "<no result returned>")

    return [name for _, name in order if name != "final_result"]


async def answer(
    message: str,
    history: list[ChatMessage] | None = None,
    customer: CustomerContext | None = None,
    page: PageContext | None = None,
) -> ChatReply:
    """Run one turn of conversation and return the validated reply."""
    agent = build_agent()
    deps = ChatDeps(
        customer=customer or CustomerContext(),
        page=page,
        page_product=resolve_page_product(page),
    )
    run_id = audit.new_run_id()
    started = time.monotonic()

    def log_run(stop_reason: str, tools_used: list[str], products: int,
                usage: Any = None, detail: str | None = None) -> None:
        audit.record_run(
            run_id,
            message=message,
            stop_reason=stop_reason,
            tools_used=tools_used,
            products_returned=products,
            signed_in=deps.customer.signed_in,
            user_id=deps.customer.user_id,
            page_product=deps.page_product.product_id if deps.page_product else None,
            duration_ms=int((time.monotonic() - started) * 1000),
            usage=usage,
            detail=detail,
        )

    try:
        result = await agent.run(
            message, message_history=build_messages(history or [], deps), deps=deps
        )
    except FILTER_ERRORS as error:
        if _is_content_filter(error):
            logger.warning("Provider content filter rejected a chat message")
            log_run("content_filter", [], 0, detail="provider rejected the prompt")
            return expand(FILTERED_REPLY)
        log_run("model_error", [], 0, detail=type(error).__name__)
        raise
    except Exception as error:
        log_run("error", [], 0, detail=type(error).__name__)
        raise

    tools_used = audit_tool_calls(run_id, result.all_messages())
    reply = expand(result.output)
    log_run("completed", tools_used, len(reply.products), usage=result.usage)
    return reply
