// Search.jsx: the search results page ("/search?q=...").
// The header's search box navigates here; this page asks the API and shows the matching chapters,
// grouped by study set, each with a snippet in which the matched words are highlighted.
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api.js";
import Highlight from "../components/Highlight.jsx";

// Results arrive best match first; keep that order while grouping them by study set.
function groupBySet(results) {
  const groups = [];
  for (const r of results) {
    let group = groups.find((g) => g.id === r.study_set_id);
    if (!group) {
      group = { id: r.study_set_id, title: r.study_set_title || "Untitled study set", results: [] };
      groups.push(group);
    }
    group.results.push(r);
  }
  return groups;
}

export default function Search() {
  const [searchParams] = useSearchParams();
  const q = (searchParams.get("q") || "").trim(); // the search words from the URL
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");

  // Search again whenever the query in the URL changes. encodeURIComponent makes spaces, quotes and
  // Greek letters safe to put in a URL.
  useEffect(() => {
    setResults(null);
    setError("");
    if (!q) return;
    api(`/api/search?q=${encodeURIComponent(q)}`)
      .then(setResults)
      .catch((err) => setError(err.message));
  }, [q]);

  if (!q) {
    return (
      <section>
        <h1>Search</h1>
        <p className="muted">Type a word or phrase in the search box to search all your study sets.</p>
      </section>
    );
  }

  return (
    <section>
      <h1>Results for “{q}”</h1>
      {error && <p className="error">{error}</p>}
      {!results && !error && <p className="muted">Searching…</p>}
      {results && results.length === 0 && (
        <p className="muted">
          No chapters match “{q}”. Try a different word, or check the spelling (accents count in Greek).
        </p>
      )}
      {results &&
        groupBySet(results).map((group) => (
          <div key={group.id} className="result-group">
            <h2>
              <Link to={`/sets/${group.id}`}>{group.title}</Link>
            </h2>
            <ul className="results">
              {group.results.map((r) => (
                <li key={r.chapter_id}>
                  <Link to={`/sets/${r.study_set_id}/chapters/${r.chapter_id}`} className="result">
                    <span className="result-title">
                      Chapter {r.chapter_position}: {r.chapter_title}
                    </span>
                    <span className="result-snippet">
                      <Highlight text={r.snippet} />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
    </section>
  );
}
