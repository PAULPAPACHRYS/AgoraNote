// Dashboard.jsx: the home page ("/"): all of the user's study sets as cards, or a welcome text.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api.js";
import ProgressBar from "../components/ProgressBar.jsx";
import { formatDate, t } from "../i18n.js";
import { setTitle, statusLabel, titleLang } from "../status.js";

export default function Dashboard() {
  const [sets, setSets] = useState(null); // null = still loading, [] = the user has no sets yet
  const [error, setError] = useState("");

  // Load the list once when the page opens (the empty [] means "only on the first render").
  useEffect(() => {
    api("/api/study-sets")
      .then(setSets)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <section>
      <div className="page-head">
        <h1>{t("dashboard.title")}</h1>
        <Link to="/new" className="button primary">{t("common.new_set")}</Link>
      </div>

      {error && <p className="error">{error}</p>}
      {!sets && !error && <p className="muted">{t("common.loading")}</p>}

      {sets && sets.length === 0 && (
        <div className="empty">
          <h2>{t("welcome.title")}</h2>
          <p>{t("welcome.intro")}</p>
          <p>{t("welcome.quizzes")}</p>
          <Link to="/new" className="button primary">{t("welcome.first_set")}</Link>
        </div>
      )}

      {sets && sets.length > 0 && (
        <ul className="cards">
          {sets.map((s) => (
            <li key={s.id}>
              <Link to={`/sets/${s.id}`} className="card">
                <span className="card-title" lang={titleLang(s)}>{setTitle(s)}</span>
                <span className={`badge badge-${s.status}`}>{statusLabel(s.status)}</span>
                {s.status === "ready" && (
                  <span className="card-progress">
                    <ProgressBar small value={s.progress.earned} max={s.progress.total} label={t("dashboard.progress")} />
                    <span className="small">{s.progress.percent}%</span>
                  </span>
                )}
                <span className="muted small">{formatDate(s.created_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
