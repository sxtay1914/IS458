import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { Icon } from './Icon';

export function Navigation() {
  const { user, login, logout } = useAuth();
  return (
    <header className="nav">
      <div className="nav-inner">
        <Link to="/" className="brand" aria-label="FashionStore home">
          <span className="brand-mark" aria-hidden="true"><Icon name="hanger" size={22} /></span>
          <span className="brand-word">fashion<b>store</b></span>
        </Link>
        <nav className="nav-links">
          <NavLink to="/" end>Shop</NavLink>
          <NavLink to="/cart">Cart</NavLink>
          {user && <NavLink to="/orders">Orders</NavLink>}
          {user ? (
            <span className="nav-user">
              <span className="avatar" aria-hidden="true">{(user.email || '?').charAt(0).toUpperCase()}</span>
              <button className="btn btn-ghost btn-sm" onClick={logout} title={user.email}>Sign out</button>
            </span>
          ) : (
            <button className="btn btn-primary btn-sm" onClick={() => void login()}>Sign in</button>
          )}
        </nav>
      </div>
    </header>
  );
}
