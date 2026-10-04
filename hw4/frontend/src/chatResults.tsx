import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { Product } from './api'

/** The products the agent returned on its most recent answer.
 *
 * The chat widget writes here; the Products page reads it. That is what lets
 * an answer in the chat redraw the grid on the page behind it, without the
 * two components knowing about each other.
 */
type ChatResults = {
  query: string
  products: Product[]
  /** Bumped on every new result, so the Products page can react to a repeat search. */
  version: number
}

type ChatResultsValue = {
  results: ChatResults | null
  setResults: (query: string, products: Product[]) => void
  clear: () => void
}

const ChatResultsContext = createContext<ChatResultsValue | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setState] = useState<ChatResults | null>(null)

  const setResults = useCallback((query: string, products: Product[]) => {
    // An answer with no products (a store-hours question, a refusal) should
    // leave whatever is already on the page alone.
    if (products.length === 0) return
    setState((prev) => ({ query, products, version: (prev?.version ?? 0) + 1 }))
  }, [])

  const clear = useCallback(() => setState(null), [])

  const value = useMemo(() => ({ results, setResults, clear }), [results, setResults, clear])
  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}

export function useChatResults(): ChatResultsValue {
  const value = useContext(ChatResultsContext)
  if (!value) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return value
}
