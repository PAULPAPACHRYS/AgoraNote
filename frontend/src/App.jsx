import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState("");

  // On the results page, keep the box showing what was searched for.
  useEffect(() => {
    if (location.pathname === "/search") {
      setQuery(new URLSearchParams(location.search).get("q") || "");
    }
  }, [location]);

  function handleSearch(event) {
    event.preventDefault();
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
