import { Link } from 'react-router-dom';
import { Icon } from './Icon';

export function NotFound() {
  return (
    <section className="empty">
      <div className="bubble bubble-muted" aria-hidden="true"><Icon name="search" size={44} /></div>
      <h1>Page not found.</h1>
      <p className="muted">That link wandered off the rack.</p>
      <Link className="btn btn-primary" to="/">Back to shop</Link>
    </section>
  );
}
