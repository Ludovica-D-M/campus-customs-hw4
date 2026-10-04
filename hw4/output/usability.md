# Campus Customs — usability improvements

Four changes: two on the website, two in the agent and backend. Each was chosen for a problem this
shop actually has, and each was tested in the running app.

---

## 1. Frontend — filter by your size, and sort the results

**What was added.** A second row of controls on the Products page: a size filter (XS–XXL, plus
*Any*) and a sort menu (Featured, Price low→high, Price high→low, Name A–Z). Picking a size shows
only products with that size genuinely in stock, and the result line reads "Showing 75 products in
stock in XS". The empty state is size-aware too — "Nothing in XS matches that" rather than a
generic message.

**Why it helps.** 145 of the 612 size rows in this catalogue are sold out — roughly a quarter of
every product-size combination. Before this, a shopper browsing 102 products had no way to avoid
the ones they could not buy; they found out by opening a product and seeing their size struck
through. Filtering by size removes that dead end entirely. Sorting by price matters because the
range runs $32–$98, and "cheapest first" is one of the most common ways people shop merchandise.

Both run on the already-loaded list, so every click is instant and costs the server nothing.

![Size filter and sort on the Products page](screenshots/usability-size-sort.png)

---

## 2. Frontend — recently viewed

**What was added.** A "Recently viewed" strip of the last eight products the shopper opened,
shown at the bottom of the Products page and of every product page. It is kept in `localStorage`,
so it survives a reload, a new tab and a return visit. The product currently open is left out, and
there is a Clear button.

**Why it helps.** Choosing between a few similar crewnecks means going back and forth, and this
catalogue has a lot of near-identical items — twelve residential-college crewnecks that differ
mainly by crest. Without a trail, comparing two means searching for the second one again.
For the shop it is the cheapest kind of merchandising: it puts things the shopper has already
shown interest in one click away, with no tracking beyond their own browser.

![Recently viewed strip](screenshots/usability-recently-viewed.png)

---

## 3. Agent — the model returns product ids, the backend builds the cards

**What was added.** The agent's output type changed from `ChatReply` (which carried whole
`ProductCard` objects) to `AgentReply`, which carries only `product_ids`. After the run, the
backend expands those ids into full cards straight from the catalogue — one query for the
catalogue rows, one for inventory — and the API still returns the same structured `ChatReply` the
frontend already consumed. Nothing changed for the website.

**Why it helps — cost.** Re-emitting six product cards costs the model about **803 output tokens**
per answer. Six ids cost about **46**. That is a **94% cut** in the product part of every
response, on the most expensive kind of token there is.

**Why it helps — accuracy.** It also closes a correctness hole. When the model wrote the cards, it
could in principle round a price, drop a size from `sizes_in_stock`, or mistype an `image_url`,
and nothing downstream would catch it. Now every field the shopper sees is read from the database
after the model has finished. The model chooses *which* products; it no longer describes them.
An id that is not in the catalogue renders nothing and is logged, rather than becoming a card for
a product that does not exist.

---

## 4. Agent — a `find_in_size` tool

**What was added.** A new tool for the question "what do you have in XXL?". One SQL join over
`catalogue` and `inventory` returns everything in stock in that size, optionally narrowed by
category and by maximum price, with a prewritten summary line ("20 in stock in XXL; showing the
first 8").

**Why it helps.** Before, that question had no good path. The agent had to call
`search_catalogue` and then `check_size` once per result — **nine tool calls** for eight
candidates, each a round trip the model waits on, and it still only covered whatever the search
happened to return. `find_in_size` answers it in **one call**, over the whole catalogue rather
than a sample.

For the shopper it turns the most natural shopping question — "what can I actually buy in my
size?" — into a direct answer. For the shop, every avoided tool call is a model round trip not
paid for and not waited on.

![Answering "what do you have in XXL under $40?"](screenshots/usability-find-in-size.png)

---

## Testing

All four were driven in the running app, in a browser, against the live backend. **21 checks, all
passing**, no console errors.

| Improvement | Checks |
|---|---|
| Size filter + sort | grid filters from 102 to 75 for XS; no sold-out card appears under a size filter; price ascending, price descending and name order each verified against the rendered values; clearing restores all 102 |
| Recently viewed | hidden when empty; shows the two earlier products after viewing three; excludes the open product; appears on the Products page too; persists into a new tab; Clear empties it; an item opens its product page |
| Ids → cards | the API still returns complete cards with `image_url` and `short_description`; cards render in the chat; the Products grid still redraws from a chat answer |
| `find_in_size` | "what do you have in XXL under $40?" — every returned card really has XXL in stock and really is under $40; the stated total of 20 matches the database |

Figures measured rather than estimated:

- Product payload the model emits: **803 → 46 tokens**, a 94% reduction.
- "What's in XXL": **1 tool call instead of 9**.
- End-to-end chat latency on fresh questions: median **5.8s**, range 4.1–12.7s.

One caveat on that last number. Repeating an identical question returns in about 0.2s, but that is
the Portkey gateway's own response cache, not anything in this code — a genuinely new question
takes the figures above. The latency improvement from these changes is the avoided tool round trips
and the shorter output, not the cache.

The existing suites still pass: **62/62** tool tests against the database, and **28/28** browser
checks across Problems 3–8.
