import { Link } from 'react-router-dom'
import { money, type Product } from '../api'

function stockBadge(product: Product) {
  const sizes = product.sizes_in_stock ?? []
  if (sizes.length === 0) return <span className="badge out">Sold out</span>
  if (sizes.length <= 2) return <span className="badge low">Only {sizes.join(', ')} left</span>
  return <span className="badge in">{sizes.length} sizes in stock</span>
}

export default function ProductCard({ product }: { product: Product }) {
  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="thumb">
        <img src={product.image_url} alt={product.name} loading="lazy" />
      </div>
      <div className="body">
        <span className="type">{product.garment_type}</span>
        <h3>{product.name}</h3>
        <p className="blurb">{product.short_description}</p>
        <div className="card-foot">
          <span className="price">{money(product.price)}</span>
          {stockBadge(product)}
        </div>
      </div>
    </Link>
  )
}
