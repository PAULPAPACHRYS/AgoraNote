import { useEffect, useState } from "react";
import { Link, Outlet } from "react-router-dom";

import { api } from "./api.js";

export default function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/health")
      .then(setHealth)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="app">
      <header className="header">
        <Link to="/" className="brand">AgoraNote</Link>
      </header>
      <main className="main">
        <p className="health">
          API status:{" "}
          {error ? (
            <span className="error">{error}</span>
          ) : health ? (
            <strong>{health.status}</strong>
          ) : (
            "checking…"
          )}
        </p>
        <Outlet />
      </main>
    </div>
  );
}
