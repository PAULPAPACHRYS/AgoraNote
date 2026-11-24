/*
 Search.jsx: the search results page ("/search?q=...")
 the header's search box navigates here, this page asks the API and shows two kinds of results:
 - study sets whose title matches (to find one set among many by its name)
 - chapters whose content matches, grouped by study set, each with a snippet in which the matched words are highlighted
 When nothing matches, a button leads back to the home screen
*/
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api.js";
import Highlight from "../components/Highlight.jsx";
import { t } from "../i18n.js";
import { statusLabel } from "../status.js";

//results arrive best match first; keep that order while grouping them by study set
function groupBySet(results) {
  const groups = [];
  for (const r of results) {
    let group = groups.find((g) => g.id === r.study_set_id);
    if (!group) {
      // lang only for a real title: the placeholder is in the interface language
      group = {
        id: r.study_set_id,
        title: r.study_set_title || t("common.untitled_set"),
        lang: r.study_set_title ? r.language : null,
        results: [],
      };
      groups.push(group);
    }
    group.results.push(r);
  }
  return groups;
}

export default function Search() {
  const [searchParams] = useSearchParams();
  const q = (searchParams.get("q") || "").trim(); //search words from the URL
  const [results, setResults] = useState(null); // { study_sets: [...], chapters: [...] }
  const [error, setError] = useState("");

  // search again whenever the query in the URL changes, encodeURIComponent makes spaces, quotes and Greek letters safe to put in a URL
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
        <h1>{t("search.title")}</h1>
        <p className="muted">{t("search.empty")}</p>
      </section>
    );
  }

  const nothingFound = results && results.study_sets.length === 0 && results.chapters.length === 0;

  return (
    <section>
      <h1>{t("search.results", { q })}</h1>
      {error && <p className="error">{error}</p>}
      {!results && !error && <p className="muted">{t("search.searching")}</p>}
      {nothingFound && (
        <>
          <p className="muted">{t("search.nothing", { q })}</p>
          <Link to="/" className="button">{t("search.home")}</Link>
        </>
      )}

      {results && results.study_sets.length > 0 && (
        <>
          <h2>{t("search.sets")}</h2>
          <ul className="results">
            {results.study_sets.map((s) => (
              <li key={s.id}>
                <Link to={`/sets/${s.id}`} className="result result-set">
                  <span className="result-title" lang={s.language}>{s.title}</span>
                  {/* the status only when it isn't simply ready, ex: "Processing" or "Failed" */}
                  {s.status !== "ready" && (
                    <span className={`badge badge-${s.status}`}>{statusLabel(s.status)}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}

      {results && results.chapters.length > 0 && <h2>{t("common.chapters")}</h2>}
      {results &&
        groupBySet(results.chapters).map((group) => (
          <div key={group.id} className="result-group">
            <h3>
              <Link to={`/sets/${group.id}`} lang={group.lang}>
                {group.title}
              </Link>
            </h3>
            <ul className="results">
              {group.results.map((r) => (
                <li key={r.chapter_id}>
                  <Link to={`/sets/${r.study_set_id}/chapters/${r.chapter_id}`} className="result">
                    <span className="result-title">
                      {t("search.chapter", {
                        n: r.chapter_position,
                        title: <span lang={r.language}>{r.chapter_title}</span>,
                      })}
                    </span>
                    {/* the snippet is the chapter's own text, in the material's language */}
                    <span className="result-snippet" lang={r.language}>
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
