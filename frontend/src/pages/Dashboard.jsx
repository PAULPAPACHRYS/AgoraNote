import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api.js";
import { setTitle, statusLabel } from "../status.js";

export default function Dashboard() {
  const [sets, setSets] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/study-sets")
      .then(setSets)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <section>
      <div className="page-head">
        <h1>Your study sets</h1>
        <Link to="/new" className="button primary">New study set</Link>
      </div>

      {error && <p className="error">{error}</p>}
      {!sets && !error && <p className="muted">Loading…</p>}

      {sets && sets.length === 0 && (
        <div className="empty">
          <h2>Welcome to AgoraNote</h2>
          <p>
            Upload lecture notes or a lecture recording, or paste some text. AgoraNote splits it into
            chapters and writes a summary, key concepts, practice questions and study aids for each one.
          </p>
          <p>
            Then test yourself with chapter quizzes: correct answers earn points, and enough points
            unlock the next chapter's quiz.
          </p>
          <Link to="/new" className="button primary">Create your first study set</Link>
        </div>
      )}

      {sets && sets.length > 0 && (
        <ul className="cards">
          {sets.map((s) => (
            <li key={s.id}>
              <Link to={`/sets/${s.id}`} className="card">
                <span className="card-title">{setTitle(s)}</span>
                <span className={`badge badge-${s.status}`}>{statusLabel(s.status)}</span>
                <span className="muted small">{new Date(s.created_at).toLocaleDateString()}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
