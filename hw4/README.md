# Campus Customs — HW4

A Yale Bulldog Blue storefront for Campus Customs: a React + Vite + TypeScript frontend, a FastAPI
backend, and a PydanticAI shopping assistant that answers from the shop's own catalogue and
inventory.

MGT 409 — AI Foundations for Managers.

---

## 1. Get the data pack in place

**The repository does not contain the database or the product images.** They are supplied
separately as a `data` folder (or `data.zip`). Put it at the project root so the tree looks like
this:

```
hw4/
├── backend/
├── frontend/
├── output/
└── data/                      ← the local-only data pack
    ├── campus_customs.db      ← catalogue, inventory, users, chat history
    └── products/              ← 102 product images
```

If you have `data.zip`, unzip it here: `unzip data.zip` from the `hw4` folder. Nothing will run
without this — the backend reads `data/campus_customs.db` directly.

## 2. Add your API key

```bash
cp .env.example .env
```

Then open `.env` and put your own Portkey key in `PORTKEY_API_KEY`. The chat assistant needs it;
the catalogue, product pages and accounts work without it. `.env` is gitignored.

## 3. Run the backend — port 8000

From the **`hw4`** folder:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

Then from the **`backend`** folder:

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

Check it: <http://localhost:8000/api/health> should report `"status": "ok"` and 102 products.

## 4. Run the frontend — port 5180

In a second terminal, from the **`frontend`** folder:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5180>.

Vite proxies `/api` and `/images` to the backend on 8000, so the page and the API are same-origin
in the browser and no extra configuration is needed. Port 5180 rather than Vite's default 5173
because 5173 was already in use during development.

## Test accounts

| Email | Password |
|---|---|
| `test@campuscustoms.yale.edu` | `password` |
| `handsome.dan@yale.edu` | `BulldogBlue2026` |

Or create your own through the site. Passwords are stored only as PBKDF2-HMAC-SHA256 digests —
see the Problem 4 section of `output/harness.md`.

## Tests

From the `backend` folder:

```bash
../.venv/bin/python test_tools.py
```

62 assertions comparing every agent tool's output against `campus_customs.db` — descriptions,
prices, in-stock and sold-out sizes, and all 102 products.

---

## Layout

```
hw4/
├── AI_prompts.md              log of every prompt used, per problem
├── requirements.txt           Python dependencies
├── .env.example               environment template — placeholders only
├── .gitignore
├── README.md
├── frontend/                  Vite React TypeScript app
│   └── src/
│       ├── api.ts             typed fetch helpers
│       ├── auth.tsx           sign-in state
│       ├── chatResults.tsx    agent results shared with the Products page
│       ├── recentlyViewed.tsx last products viewed, in localStorage
│       ├── components/        Nav, Footer, ProductCard, ChatWidget, Labubu, …
│       └── pages/             Home, Products, ProductDetail, About, Login, …
├── backend/
│   ├── main.py                FastAPI app — uvicorn main:app --reload --port 8000
│   ├── agent.py               the PydanticAI agent: model, prompt, tools, audit
│   ├── models.py              typed contracts for tools, chat and product cards
│   ├── tools.py               catalogue lookups, shared by the agent and the API
│   ├── auth.py                password hashing and signed session cookies
│   ├── audit.py               the append-only audit trail
│   ├── test_tools.py          tool tests against the database
│   └── prompts/
│       └── prompt.md          system prompt: voice, answering rules, safety rules
└── output/
    ├── harness.md             how the system works, and notes for every problem
    ├── design.md              the visual design and why
    ├── usability.md           the four usability improvements
    ├── app_check.html         live-site checks — open by double-clicking
    ├── app_check_images/      screenshots linked from app_check.html
    ├── screenshots/           screenshots linked from the markdown write-ups
    └── audit_trail.json       append-only record of agent-loop activity
```

## API

| Endpoint | Returns |
|---|---|
| `GET /api/health` | status plus product count |
| `GET /api/products` | the catalogue; `search`, `garment_type`, `in_stock_only` |
| `GET /api/garment-types` | categories for the filter chips |
| `GET /api/products/{id}` | one product with per-size inventory |
| `GET /api/products/{id}/inventory` | per-size stock |
| `GET /images/{file}.jpg` | product photo from `data/products/` |
| `POST /api/auth/register` | create an account and sign in |
| `POST /api/auth/login` | sign in |
| `POST /api/auth/logout` | sign out |
| `GET /api/auth/me` | the signed-in user, or `null` |
| `POST /api/chat` | send a message to the shopping assistant |
| `GET /api/chat/history` | a signed-in customer's saved conversation |

## Notes

- Model: `gpt-5.6-luna` through the Portkey gateway, on the Responses endpoint.
- The API key is read from the environment only — it is in no source file, log or bundle.
- `output/harness.md` has the full reference: model fields, tools, safety rules, loop limits and
  caps.

This is coursework — a student recreation of the Campus Customs storefront, not the live shop.
