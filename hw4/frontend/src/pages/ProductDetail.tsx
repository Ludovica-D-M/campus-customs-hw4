import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, money, type ProductDetail as Detail } from '../api'
import RecentlyViewed from '../components/RecentlyViewed'
import { useRecentlyViewed } from '../recentlyViewed'
import { useReveal } from '../useReveal'

export default function ProductDetail() {
  const { productId } = useParams<{ productId: string }>()
  const { remember } = useRecentlyViewed()
  const [product, setProduct] = useState<Detail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [size, setSize] = useState<string | null>(null)
  useReveal([product?.product_id])

  useEffect(() => {
    if (!productId) return
    setProduct(null)
    setError(null)
    setSize(null)
    api
      .product(productId)
      .then((p) => {
        setProduct(p)
        remember(p)
      })
      .catch(() => setError('We could not find that product.'))
    // `remember` is stable; re-running on it would loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId])

  if (error) {
    return (
      <div className="wrap section">
        <p className="state">{error} <Link to="/products">Back to all products</Link></p>
      </div>
    )
  }
  if (!product) {
    return <div className="wrap section"><p className="state">Loading…</p></div>
  }

  const selected = product.inventory.find((s) => s.size === size)

  return (
    <div className="wrap">
      <p className="crumbs">
        <Link to="/">Home</Link> / <Link to="/products">Products</Link> / {product.name}
      </p>

      <div className="detail" style={{ paddingBottom: 48 }}>
        <div className="photo">
          <img src={product.image_url} alt={product.name} />
        </div>

        <div>
          <span className="eyebrow" style={{ fontSize: 10.5, color: 'var(--brass)' }}>
            {product.garment_type}
          </span>
          <h1>{product.name}</h1>

          <div className="price-row">
            <span className="price">{money(product.price)}</span>
            {product.sizes_in_stock.length > 0 ? (
              <span className="badge in">In stock</span>
            ) : (
              <span className="badge out">Sold out</span>
            )}
          </div>

          <p>{product.description}</p>

          <h3 style={{ fontSize: 17, marginTop: 28 }}>Sizes &amp; stock</h3>
          <div className="sizes">
            {product.inventory.map((s) => {
              const sold = s.quantity === 0
              return (
                <button
                  key={s.size}
                  className={`size-box${sold ? ' sold' : ''}`}
                  disabled={sold}
                  onClick={() => setSize(s.size)}
                  style={{
                    cursor: sold ? 'not-allowed' : 'pointer',
                    borderColor: size === s.size ? 'var(--yale-blue)' : undefined,
                    borderWidth: size === s.size ? 2 : 1,
                    fontFamily: 'inherit',
                  }}
                >
                  <strong>{s.size}</strong>
                  <span>{sold ? 'Sold out' : `${s.quantity} left`}</span>
                </button>
              )
            })}
          </div>

          <p style={{ marginTop: 18 }}>
            <button className="btn" disabled={!selected || selected.quantity === 0}>
              {selected ? `Add ${selected.size} to bag` : 'Select a size'}
            </button>
          </p>

          <dl style={{ marginTop: 30 }}>
            <div className="spec">
              <dt>Colors</dt>
              <dd>{product.colors.length ? product.colors.join(', ') : '—'}</dd>
            </div>
            <div className="spec">
              <dt>Price</dt>
              <dd>{money(product.price)}</dd>
            </div>
            <div className="spec">
              <dt>Total stock</dt>
              <dd>{product.total_stock} units across {product.inventory.length} sizes</dd>
            </div>
            <div className="spec">
              <dt>Product ID</dt>
              <dd><code>{product.product_id}</code></dd>
            </div>
            <div className="spec">
              <dt>Tags</dt>
              <dd>
                <div className="tags">
                  {product.search_tags.map((t) => <span className="tag" key={t}>{t}</span>)}
                </div>
              </dd>
            </div>
          </dl>
        </div>
      </div>

      <RecentlyViewed exclude={product.product_id} />
    </div>
  )
}
