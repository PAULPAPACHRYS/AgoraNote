// ErrorPage.jsx: the friendly page shown when a page crashes while drawing itself (a bug), instead of
// a blank screen. React Router shows it through `errorElement` (see main.jsx) and hands over the
// error, which useRouteError() reads.
//
// It is used in two places:
// - around the pages: the error shows inside the normal layout, so the header still works;
// - around the whole app (`standalone`): for errors in the layout itself, so it draws its own simple
//   header and doesn't rely on anything that may be broken (like the sign-in components).
import { Link, isRouteErrorResponse, useRouteError } from "react-router-dom";

import NotFound from "./NotFound.jsx";

export default function ErrorPage({ standalone = false }) {
  const error = useRouteError();

  // The router itself reports an unknown URL as a 404 "error"; the "*" route normally catches those
  // first, but if one gets here it gets the proper not-found page rather than "something went wrong".
  const notFound = isRouteErrorResponse(error) && error.status === 404;

  const content = notFound ? (
    <NotFound />
  ) : (
    <section className="empty" role="alert">
      <h1>Something went wrong</h1>
      <p>
        Sorry, this page ran into a problem and couldn't be shown. Your study sets and points are safe:
        they are stored on the server. Try loading the page again, or go back to your study sets.
      </p>
      <div className="actions">
        {/* a full reload starts the app afresh, which fixes most one-off problems */}
        <button type="button" className="primary" onClick={() => window.location.reload()}>
          Try again
        </button>
        <Link to="/" className="button">Back to your study sets</Link>
      </div>
      {/* the technical details help while developing; users of the built app don't see them */}
      {import.meta.env.DEV && (
        <details className="error-details">
          <summary>Error details (development only)</summary>
          <pre>{error instanceof Error ? error.stack || error.message : JSON.stringify(error, null, 2)}</pre>
        </details>
      )}
    </section>
  );

  if (!standalone) return content;
  return (
    <div className="app">
      <header className="header">
        <Link to="/" className="brand">AgoraNote</Link>
      </header>
      <main className="main">{content}</main>
    </div>
  );
}
