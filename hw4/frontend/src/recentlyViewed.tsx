import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Product } from './api'

const KEY = 'cc_recently_viewed'
const MAX = 8

/** The last few products the shopper opened, kept in localStorage.
 *
 * Survives a reload and a new tab, so someone comparing a few crewnecks can
 * get back to the one they liked without searching for it again.
 */
type Value = {
  recent: Product[]
  remember: (product: Product) => void
  clear: () => void
}

const Ctx = createContext<Value | null>(null)

function read(): Product[] {
  try {
    const raw = localStorage.getItem(KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.slice(0, MAX) : []
  } catch {
    return []
  }
}

export function RecentlyViewedProvider({ children }: { children: ReactNode }) {
  const [recent, setRecent] = useState<Product[]>([])

  useEffect(() => setRecent(read()), [])

  const remember = useCallback((product: Product) => {
    setRecent((prev) => {
      const next = [product, ...prev.filter((p) => p.product_id !== product.product_id)].slice(0, MAX)
      try {
        localStorage.setItem(KEY, JSON.stringify(next))
      } catch {
        /* private browsing, quota — not worth breaking the page over */
      }
      return next
    })
  }, [])

  const clear = useCallback(() => {
    setRecent([])
    try {
      localStorage.removeItem(KEY)
    } catch {
      /* ignore */
    }
  }, [])

  const value = useMemo(() => ({ recent, remember, clear }), [recent, remember, clear])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useRecentlyViewed(): Value {
  const value = useContext(Ctx)
  if (!value) throw new Error('useRecentlyViewed must be used inside <RecentlyViewedProvider>')
  return value
}
