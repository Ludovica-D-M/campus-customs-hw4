import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { money, type Product } from '../api'
import { useAuth, greetingName } from '../auth'
import { useChatResults } from '../chatResults'

type Message = {
  role: 'user' | 'assistant'
  content: string
  products?: Product[]
}

const GREETING: Message = {
  role: 'assistant',
  content:
    "Hi! I'm the Campus Customs shopping assistant. Ask me about hoodies, crewnecks, " +
    'residential college gear, colors, or what we have in your size.',
}

const OPENERS = [
  'What hoodies do you have?',
  'Anything in gray under $50?',
  'Do you have Saybrook gear in L?',
]

export default function ChatWidget() {
  const { setResults } = useChatResults()
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [params] = useSearchParams()
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [thinking, setThinking] = useState(false)
  const [messages, setMessages] = useState<Message[]>([GREETING])
  const [suggestions, setSuggestions] = useState<string[]>(OPENERS)
  const [restored, setRestored] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, thinking, open])

  // Reload a signed-in customer's saved conversation, and drop back to a
  // clean greeting when they sign out.
  useEffect(() => {
    if (authLoading) return
    if (!user) {
      setMessages([GREETING])
      setSuggestions(OPENERS)
      setRestored(false)
      return
    }
    let cancelled = false
    fetch('/api/chat/history', { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : { messages: [] }))
      .then((data) => {
        if (cancelled) return
        const saved: Message[] = (data.messages ?? []).map(
          (m: { role: 'user' | 'assistant'; content: string; products?: Product[] }) => ({
            role: m.role,
            content: m.content,
            products: m.products ?? [],
          }),
        )
        setMessages(saved.length ? [GREETING, ...saved] : [GREETING])
        setRestored(saved.length > 0)
        if (saved.length) setSuggestions([])
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [user, authLoading])

  /** What the customer is looking at while they type, so "this" resolves.
   *
   * The widget lives in the layout route, so it cannot read the child route's
   * params — the product id is taken from the path instead.
   */
  function pageContext() {
    const onProduct = pathname.match(/^\/products\/([^/]+)$/)
    return {
      path: pathname,
      product_id: onProduct ? decodeURIComponent(onProduct[1]) : null,
      category: params.get('category'),
    }
  }

  async function send(text: string) {
    const content = text.trim()
    if (!content || thinking) return

    // The agent needs the thread to resolve follow-ups like "in gray?".
    const history = messages
      .filter((m) => m !== GREETING)
      .map((m) => ({ role: m.role, content: m.content }))

    setMessages((prev) => [...prev, { role: 'user', content }])
    setDraft('')
    setSuggestions([])
    setThinking(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        credentials: 'include',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ message: content, history, page: pageContext() }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? 'The shopping assistant is unavailable right now.')
      }
      const reply = await res.json()
      const products: Product[] = reply.products ?? []
      setMessages((prev) => [...prev, { role: 'assistant', content: reply.message, products }])
      setSuggestions(reply.suggestions ?? [])
      // Publish the agent's matches so the Products page can render them as
      // full cards. The grid redraws whether or not the shopper is looking
      // at it right now.
      setResults(content, products)
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            err instanceof Error
              ? err.message
              : 'Something went wrong reaching the shopping assistant.',
        },
      ])
    } finally {
      setThinking(false)
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    send(draft)
  }

  if (!open) {
    return (
      <button className="chat-launcher" onClick={() => setOpen(true)} aria-label="Open shopping assistant">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 9 9 0 0 1-3.9-.9L3 20.5l1.6-4.6A8.4 8.4 0 0 1 3.6 11 8.4 8.4 0 0 1 12 2.6a8.4 8.4 0 0 1 9 8.9z" />
        </svg>
      </button>
    )
  }

  return (
    <section className="chat-panel" aria-label="Campus Customs shopping assistant">
      <header className="chat-head">
        <span className="avatar">Y</span>
        <span className="who">
          <strong>Campus Customs Assistant</strong>
          <span>
            {thinking
              ? 'Checking the shelves…'
              : user
                ? `Signed in as ${greetingName(user)} · chat saved`
                : 'Ask about stock, sizes and colors'}
          </span>
        </span>
        <button onClick={() => setOpen(false)} aria-label="Close chat">×</button>
      </header>

      <div className="chat-log" ref={logRef}>
        {restored && <div className="chat-restored">Picking up where you left off</div>}
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'turn me' : 'turn bot'}>
            <div className={m.role === 'user' ? 'bubble me' : 'bubble bot'}>{m.content}</div>
            {m.products && m.products.length > 0 && (
              <>
                <div className="chat-products">
                  {m.products.map((p) => (
                    <Link
                      key={p.product_id}
                      to={`/products/${p.product_id}`}
                      className="chat-product"
                      onClick={() => setOpen(false)}
                    >
                      <img src={p.image_url} alt={p.name} loading="lazy" />
                      <span className="chat-product-body">
                        <strong>{p.name}</strong>
                        <span className="chat-product-blurb">{p.short_description}</span>
                        <span className="chat-product-meta">
                          {money(p.price)}
                          {p.sizes_in_stock && p.sizes_in_stock.length > 0
                            ? ` · ${p.sizes_in_stock.join(', ')}`
                            : ' · sold out'}
                        </span>
                      </span>
                    </Link>
                  ))}
                </div>
                <button
                  className="chat-see-on-page"
                  onClick={() => {
                    setResults(
                      messages[i - 1]?.content ?? 'your question',
                      m.products as Product[],
                    )
                    navigate('/products')
                  }}
                >
                  {pathname === '/products'
                    ? `Showing these ${m.products.length} on the page →`
                    : `See these ${m.products.length} on the page →`}
                </button>
              </>
            )}
          </div>
        ))}
        {thinking && (
          <div className="bubble bot">
            <span className="typing"><i /><i /><i /></span>
          </div>
        )}
      </div>

      {suggestions.length > 0 && !thinking && (
        <div className="chat-suggestions">
          {suggestions.map((s) => (
            <button key={s} onClick={() => send(s)}>{s}</button>
          ))}
        </div>
      )}

      <form className="chat-input" onSubmit={onSubmit}>
        <input
          type="text"
          value={draft}
          placeholder="Ask about a product, size, or color…"
          onChange={(e) => setDraft(e.target.value)}
          aria-label="Message"
        />
        <button type="submit" disabled={!draft.trim() || thinking} aria-label="Send">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 2 11 13M22 2l-7 20-4-9-9-4z" />
          </svg>
        </button>
      </form>
    </section>
  )
}
