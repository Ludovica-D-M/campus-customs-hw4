import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './auth'
import { ChatResultsProvider } from './chatResults'
import { RecentlyViewedProvider } from './recentlyViewed'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import About from './pages/About'
import Login from './pages/Login'
import CreateAccount from './pages/CreateAccount'
import Account from './pages/Account'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <ChatResultsProvider>
        <RecentlyViewedProvider>
          <BrowserRouter>
          <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<Home />} />
          <Route path="products" element={<Products />} />
          <Route path="products/:productId" element={<ProductDetail />} />
          <Route path="about" element={<About />} />
          <Route path="login" element={<Login />} />
          <Route path="create-account" element={<CreateAccount />} />
          <Route path="account" element={<Account />} />
          <Route path="*" element={<Home />} />
        </Route>
          </Routes>
          </BrowserRouter>
        </RecentlyViewedProvider>
      </ChatResultsProvider>
    </AuthProvider>
  </StrictMode>,
)
