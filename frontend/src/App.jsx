// App.jsx: the layout around every page: the header (app name + search box) and the page itself.
import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";

export default function App() {
  // navigate(url) changes the page from code; location is the current URL.
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState(""); // what is typed in the search box

  // On the results page, keep the box showing what was searched for.
  useEffect(() => {
    if (location.pathname === "/search") {
      setQuery(new URLSearchParams(location.search).get("q") || "");
    }
  }, [location]);

  // Enter in the search box: go to the results page (an empty search does nothing).
  function handleSearch(event) {
    event.preventDefault(); // stop the browser's default form submit (a full page reload)
    if (query.trim()) navigate(`/search?q=${encodeURIComponent(query.trim())}`);
  }

  return (
    <div className="app">
      <header className="header">
        <Link to="/" className="brand">AgoraNote</Link>
        <form className="search-form" role="search" onSubmit={handleSearch}>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search your study sets"
            aria-label="Search your study sets"
            maxLength={200}
          />
        </form>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
