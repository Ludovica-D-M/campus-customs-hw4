export default function About() {
  return (
    <div className="wrap section">
      <div className="prose">
        <span className="eyebrow" style={{ color: 'var(--brass)', fontSize: 11, display: 'block', marginBottom: 12 }}>57 Broadway, New Haven</span>
        <h1>About Campus Customs</h1>
        <p>
          Campus Customs is an officially licensed Yale merchandise shop at 57 Broadway in New
          Haven, a few minutes' walk from Old Campus. Yale Bulldog Blue is the name the shop
          trades under online, so what you find here is the same licensed apparel that sits on
          the shelves in the store.
        </p>

        <h2>What we carry</h2>
        <p>
          The heart of the shop is clothing: t-shirts, hoodies, crewnecks, quarter-zips, jackets,
          activewear, polos and bottoms, sized for men, women, youth and infants. Alongside the
          apparel the shop stocks hats, bags and jewelry, drinkware, office supplies and home
          décor.
        </p>
        <p>
          Collections are organized the way Yale itself is. There is gear for the residential
          colleges, for the graduate and professional schools, and for the varsity teams, plus
          class-year collections for current students and merchandise for alumni. Some pieces are
          made under our own label; others come from brands like Champion and Brooks Brothers.
          Prices run from a few dollars for small accessories up to premium outerwear.
        </p>

        <h2 id="shipping">Shipping</h2>
        <p>
          Most orders are produced within five to eight business days, and shipping starts once
          production is finished — peak periods can stretch that out. Domestic orders usually go
          out by UPS, though another carrier may be used when it gets the package there sooner.
          A confirmation email with tracking goes out as soon as the order ships.
        </p>
        <p>
          We also ship internationally, to more than thirty countries. International delivery
          times vary with the destination and with customs processing, and any duties, taxes or
          import charges are the customer's responsibility. Carrier delays from weather or
          holidays do happen occasionally, so estimated dates are estimates.
        </p>

        <h2 id="returns">Returns and exchanges</h2>
        <p>
          You have thirty days from the shipping date to return an item. It has to come back
          unworn and unused with its original tags and labels attached. Final sale items cannot
          be refunded, and custom products — including the Custom Alumni line — are final sale,
          so they are not eligible for return or exchange.
        </p>
        <p>
          If the return is because of a mistake on our end, we cover the return shipping. If you
          simply changed your mind, the return shipping is yours to cover; email the tracking
          number to <a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a>{' '}
          so we can watch for the package. Refunds do not include the original shipping cost and
          can take two to ten business days to show up, depending on your bank. On an exchange,
          we email tracking once the replacement ships.
        </p>

        <h2>Find us</h2>
        <div className="info-grid">
          <div className="card">
            <h3>Store</h3>
            <p>57 Broadway<br />New Haven, CT 06511</p>
          </div>
          <div className="card">
            <h3>Phone</h3>
            <p>(475) 301-4205</p>
          </div>
          <div className="card">
            <h3>Email</h3>
            <p><a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a></p>
          </div>
        </div>

        <p style={{ marginTop: 36, fontSize: 14, color: '#7a8899' }}>
          This site is a coursework recreation of the Campus Customs storefront built for
          MGT 409. The store details above are drawn from the real yalebulldogblue.com; the
          catalogue and stock numbers come from the course database.
        </p>
      </div>
    </div>
  )
}
