import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Product } from '../api'
import { useReveal } from '../useReveal'
import ProductCard from '../components/ProductCard'

export default function Home() {
  const [featured, setFeatured] = useState<Product[]>([])
  useReveal([featured.length])

  useEffect(() => {
    api.products().then((data) => {
      const inStock = data.products.filter((p) => (p.sizes_in_stock ?? []).length > 2)
      setFeatured(inStock.slice(0, 4))
    }).catch(() => setFeatured([]))
  }, [])

  return (
    <>
      <section className="hero">
        <div className="wrap">
          <p className="eyebrow">Officially licensed Yale apparel</p>
          <h1>Yale Bulldog Blue,<br /><em>made on Broadway.</em></h1>
          <p>
            Campus Customs has outfitted New Haven from its shop at 57 Broadway for years, and
            Yale Bulldog Blue is where that same licensed apparel lives online. Hoodies,
            crewnecks, quarter-zips and tees for every residential college, graduate school and
            varsity team — plus house-brand basics alongside names like Champion and
            Brooks Brothers.
          </p>
          <div className="hero-actions">
            <Link className="btn ghost" to="/products">Shop all products</Link>
            <Link className="btn gold" to="/create-account">Create an account</Link>
          </div>
        </div>
      </section>

      <div className="stripe">
        <div className="wrap reveal">
          <div className="stat">
            <strong>5–8</strong>
            <span>business days to produce most orders</span>
          </div>
          <div className="stat">
            <strong>30+</strong>
            <span>countries we ship to</span>
          </div>
          <div className="stat">
            <strong>30 days</strong>
            <span>to return unworn items with tags</span>
          </div>
          <div className="stat">
            <strong>57 Broadway</strong>
            <span>our shop in New Haven</span>
          </div>
        </div>
      </div>

      <section className="section">
        <div className="wrap reveal">
          <div className="section-head">
            <span className="eyebrow">The shop floor</span>
            <h2>Shop by category</h2>
            <p>Four things people walk in asking for, and the ones they order the most online.</p>
          </div>
          <div className="cards">
            <Link className="card" to="/products?category=hood">
              <h3>Hoodies</h3>
              <p>Pullovers and full-zips, from the big-YALE classic to Champion reverse weave.</p>
            </Link>
            <Link className="card" to="/products?category=crewneck">
              <h3>Crewnecks</h3>
              <p>Residential college and team crewnecks — the largest part of the catalogue.</p>
            </Link>
            <Link className="card" to="/products?category=t-shirt">
              <h3>T-shirts</h3>
              <p>Lightweight tees, tri-blends and the Harvard–Yale game shirt.</p>
            </Link>
            <Link className="card" to="/products?category=quarter-zip">
              <h3>Quarter-zips</h3>
              <p>School-by-school quarter-zips for Law, Music, Art, Engineering and Public Health.</p>
            </Link>
          </div>
        </div>
      </section>

      <section className="section tight">
        <div className="wrap reveal">
          <div className="section-head">
            <span className="eyebrow">On the shelf today</span>
            <h2>In stock right now</h2>
            <p>A few pieces with the fullest size runs on the shelf today.</p>
          </div>
          {featured.length === 0 ? (
            <p className="state">Loading the catalogue…</p>
          ) : (
            <div className="grid">
              {featured.map((p) => <ProductCard key={p.product_id} product={p} />)}
            </div>
          )}
          <p style={{ marginTop: 28 }}>
            <Link className="btn outline" to="/products">See the full catalogue</Link>
          </p>
        </div>
      </section>

      <section className="section tight">
        <div className="wrap reveal">
          <div className="cards">
            <div className="card">
              <h3>Licensed, not knock-off</h3>
              <p>Everything here is officially licensed Yale merchandise.</p>
            </div>
            <div className="card">
              <h3>Shipped from New Haven</h3>
              <p>Domestic orders usually travel by UPS, with tracking emailed when they leave.</p>
            </div>
            <div className="card">
              <h3>Ask before you buy</h3>
              <p>Use the chat in the corner for sizes, colors and what is actually on the shelf.</p>
            </div>
          </div>
        </div>
      </section>
    </>
  )
}
