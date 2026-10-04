import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="site">
      <div className="wrap">
        <div>
          <h4>Campus Customs</h4>
          <p>
            Yale Bulldog Blue is the online shop of Campus Customs, the officially licensed
            Yale apparel store on Broadway in New Haven.
          </p>
        </div>
        <div>
          <h4>Shop</h4>
          <Link to="/products">All products</Link>
          <Link to="/products?category=hood">Hoodies</Link>
          <Link to="/products?category=crewneck">Crewnecks</Link>
          <Link to="/products?category=t-shirt">T-shirts</Link>
        </div>
        <div>
          <h4>Help</h4>
          <Link to="/about">About us</Link>
          <Link to="/about#shipping">Shipping</Link>
          <Link to="/about#returns">Returns</Link>
          <Link to="/login">Your account</Link>
        </div>
        <div>
          <h4>Visit</h4>
          <p>
            57 Broadway<br />
            New Haven, CT 06511<br />
            (475) 301-4205<br />
            orderdept@campuscustoms.com
          </p>
        </div>
      </div>
      <div className="wrap">
        <div className="colophon">
          Coursework build for MGT 409 — a student recreation of the Campus Customs storefront,
          not the live shop.
        </div>
      </div>
    </footer>
  )
}
