import { Link } from 'react-router-dom'
import { money } from '../api'
import { useRecentlyViewed } from '../recentlyViewed'

export default function RecentlyViewed({ exclude }: { exclude?: string }) {
  const { recent, clear } = useRecentlyViewed()
  const items = recent.filter((p) => p.product_id !== exclude)
  if (items.length === 0) return null

  return (
    <section className="recent">
      <div className="recent-head">
        <h2>Recently viewed</h2>
        <button className="chip" onClick={clear}>Clear</button>
      </div>
      <div className="recent-strip">
        {items.map((p) => (
          <Link key={p.product_id} to={`/products/${p.product_id}`} className="recent-item">
            <img src={p.image_url} alt={p.name} loading="lazy" />
            <span className="recent-name">{p.name}</span>
            <span className="recent-price">{money(p.price)}</span>
          </Link>
        ))}
      </div>
    </section>
  )
}
