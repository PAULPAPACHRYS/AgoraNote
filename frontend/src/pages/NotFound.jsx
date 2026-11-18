// NotFound.jsx: the "page not found" page, for any URL that matches no route (the "*" route in
// main.jsx). It is shown inside the normal layout, so the header and search box are still there.
import { Link, useLocation } from "react-router-dom";

export default function NotFound() {
  const location = useLocation(); // the address that was asked for, shown so typos are easy to spot

  return (
    <section className="empty">
      <h1>Page not found</h1>
      <p>
        There is no page at <code>{location.pathname}</code>. The link may be mistyped, or the page
        may have been moved or deleted.
      </p>
      <div className="actions">
        <Link to="/" className="button primary">Back to your study sets</Link>
        <Link to="/new" className="button">New study set</Link>
      </div>
    </section>
  );
}
