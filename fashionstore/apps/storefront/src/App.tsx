import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { ApiProvider } from './api/ApiContext';
import { AuthProvider } from './auth/AuthContext';
import { Navigation } from './components/Navigation';
import { AuthCallbackPage } from './pages/AuthCallbackPage';
import { CartPage } from './pages/CartPage';
import { CheckoutPage } from './pages/CheckoutPage';
import { CheckoutStatusPage } from './pages/CheckoutStatusPage';
import { OrderDetailsPage } from './pages/OrderDetailsPage';
import { OrdersPage } from './pages/OrdersPage';
import { ProductDetailsPage } from './pages/ProductDetailsPage';
import { ProductsPage } from './pages/ProductsPage';
import type { AppConfig } from './types';

export function App({ config }: { config: AppConfig }) {
  return (
    <AuthProvider config={config}>
      <ApiProvider apiBase={config.apiBase}>
        <BrowserRouter>
          <Navigation />
          <main>
            <Routes>
              <Route path="/" element={<ProductsPage />} />
              <Route path="/products/:sku" element={<ProductDetailsPage />} />
              <Route path="/cart" element={<CartPage />} />
              <Route path="/checkout" element={<CheckoutPage />} />
              <Route path="/checkout/:checkoutId" element={<CheckoutStatusPage />} />
              <Route path="/orders" element={<OrdersPage />} />
              <Route path="/orders/:orderId" element={<OrderDetailsPage />} />
              <Route path="/auth/callback" element={<AuthCallbackPage config={config} />} />
              <Route path="*" element={<p>Page not found.</p>} />
            </Routes>
          </main>
        </BrowserRouter>
      </ApiProvider>
    </AuthProvider>
  );
}
