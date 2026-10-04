import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, type Category, type Product } from '../api'
import ProductCard from '../components/ProductCard'
import { useChatResults } from '../chatResults'
import RecentlyViewed from '../components/RecentlyViewed'
import SkeletonGrid from '../components/SkeletonGrid'
import { useReveal } from '../useReveal'

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

export default function Products() {
  const [params, setParams] = useSearchParams()
  const { results: chatResults, clear: clearChatResults } = useChatResults()
  const category = params.get('category') ?? ''
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [query, setQuery] = useState('')
  const [size, setSize] = useState('')
  const [sort, setSort] = useState<'featured' | 'price-asc' | 'price-desc' | 'name'>('featured')
  const [loading, setLoading] = useState(true)
  useReveal([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.categories().then((d) => setCategories(d.categories)).catch(() => setCategories([]))
  }, [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    api
      .products({ garment_type: category || undefined })
      .then((d) => setProducts(d.products))
      .catch(() => setError('Could not reach the catalogue. Is the backend running on port 8000?'))
      .finally(() => setLoading(false))
  }, [category])

  // Filter and sort in the browser so every control feels instant.
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()
    let list = products

    if (needle) {
      list = list.filter((p) =>
        [p.name, p.garment_type, p.description, ...p.colors, ...p.search_tags]
          .join(' ')
          .toLowerCase()
          .includes(needle),
      )
    }

    // About a quarter of all size combinations are sold out, so "only show me
    // what I can actually buy in my size" saves a lot of dead ends.
    if (size) list = list.filter((p) => (p.sizes_in_stock ?? []).includes(size))

    const sorted = [...list]
    if (sort === 'price-asc') sorted.sort((a, b) => a.price - b.price)
    else if (sort === 'price-desc') sorted.sort((a, b) => b.price - a.price)
    else if (sort === 'name') sorted.sort((a, b) => a.name.localeCompare(b.name))
    return sorted
  }, [products, query, size, sort])

  function pick(match: string) {
    // Choosing a category is a deliberate browse, so it replaces whatever the
    // assistant last put on the page.
    clearChatResults()
    const next = new URLSearchParams(params)
    if (match && match !== category) next.set('category', match)
    else next.delete('category')
    setParams(next)
  }

  // When the assistant has answered with products, those are what the page
  // shows — same ProductCard as a normal browse, so the cards look and behave
  // identically and link to the same detail pages.
  const showingChatResults = chatResults !== null
  const shown = showingChatResults ? chatResults.products : visible

  return (
    <div className="wrap section">
      <div className="section-head">
        <span className="eyebrow">The full catalogue</span>
        <h1>Products</h1>
        <p>Everything Campus Customs is carrying right now, straight from the shop's catalogue.</p>
      </div>

      <div className="toolbar">
        <input
          type="search"
          value={query}
          placeholder="Search by name, color, school or team…"
          onChange={(e) => {
            clearChatResults()
            setQuery(e.target.value)
          }}
          aria-label="Search products"
        />
        <div className="chips">
          <button className={category ? 'chip' : 'chip active'} onClick={() => pick('')}>
            All
          </button>
          {categories.map((c) => (
            <button
              key={c.match}
              className={category === c.match ? 'chip active' : 'chip'}
              onClick={() => pick(c.match)}
            >
              {c.label} ({c.count})
            </button>
          ))}
        </div>
      </div>

      <div className="toolbar toolbar-second">
        <span className="toolbar-label">My size</span>
        <div className="chips">
          <button className={size ? 'chip' : 'chip active'} onClick={() => setSize('')}>Any</button>
          {SIZES.map((s) => (
            <button
              key={s}
              className={size === s ? 'chip active' : 'chip'}
              onClick={() => {
                clearChatResults()
                setSize(size === s ? '' : s)
              }}
            >
              {s}
            </button>
          ))}
        </div>
        <span className="toolbar-label">Sort</span>
        <select
          className="sort-select"
          value={sort}
          onChange={(e) => setSort(e.target.value as typeof sort)}
          aria-label="Sort products"
        >
          <option value="featured">Featured</option>
          <option value="price-asc">Price: low to high</option>
          <option value="price-desc">Price: high to low</option>
          <option value="name">Name A–Z</option>
        </select>
      </div>

      {showingChatResults && (
        <div className="assistant-banner">
          <span className="assistant-badge">From the assistant</span>
          <p>
            {shown.length} {shown.length === 1 ? 'match' : 'matches'} for
            {' '}&ldquo;{chatResults.query}&rdquo;
          </p>
          <button className="chip" onClick={clearChatResults}>Show all products</button>
        </div>
      )}

      {error && <p className="state">{error}</p>}
      {!error && loading && !showingChatResults && <SkeletonGrid count={8} />}
      {!error && (!loading || showingChatResults) && (
        <>
          {!showingChatResults && (
            <p style={{ marginTop: 0, fontSize: 14, color: '#7a8899' }}>
              Showing {shown.length} {shown.length === 1 ? 'product' : 'products'}
              {size ? ` in stock in ${size}` : ''}
            </p>
          )}
          {shown.length === 0 ? (
            <p className="state">
              {size
                ? `Nothing in ${size} matches that. Try another size or clear the filter.`
                : 'Nothing matched that search. Try a color, a sport or a college name.'}
            </p>
          ) : (
            <div className="grid">
              {shown.map((p) => <ProductCard key={p.product_id} product={p} />)}
            </div>
          )}
        </>
      )}

      <RecentlyViewed />
    </div>
  )
}
