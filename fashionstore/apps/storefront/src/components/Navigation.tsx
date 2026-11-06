import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export function Navigation() {
  const { user, login, logout } = useAuth();
  return (
    <header className="nav">
      <Link to="/" className="brand">FASHIONSTORE</Link>
      <nav>
        <NavLink to="/">Shop</NavLink>
        <NavLink to="/cart">Cart</NavLink>
        {user && <NavLink to="/orders">Orders</NavLink>}
        {user ? (
          <button className="link" onClick={logout} title={user.email}>Sign out</button>
        ) : (
          <button className="link" onClick={() => void login()}>Sign in</button>
        )}
      </nav>
    </header>
  );
}
