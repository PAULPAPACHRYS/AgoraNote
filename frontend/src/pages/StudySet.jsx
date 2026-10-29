import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api.js";
import ChapterList from "../components/ChapterList.jsx";
import { setTitle, statusLabel } from "../status.js";

const POLL_MS = 3000;

function isFinished(status) {
  return status === "ready" || status === "failed";
}

export default function StudySet() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [studySet, setStudySet] = useState(null);
  const [error, setError] = useState("");
  const [pollKey, setPollKey] = useState(0); // bumped by Retry to start polling again
  const [retrying, setRetrying] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Load the set, then keep polling while it is being processed.
  useEffect(() => {
    let timer = null;
    function load() {
      api(`/api/study-sets/${id}`)
        .then((data) => {
          setStudySet(data);
          setError("");
          if (isFinished(data.status)) clearInterval(timer);
        })
        .catch((err) => setError(err.message));
    }
    load();
    timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [id, pollKey]);

  async function handleRetry() {
    setRetrying(true);
    try {
      setStudySet(await api(`/api/study-sets/${id}/retry`, { method: "POST" }));
      setPollKey((k) => k + 1);
    } catch (err) {
      setError(err.message);
    }
    setRetrying(false);
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await api(`/api/study-sets/${id}`, { method: "DELETE" });
      navigate("/");
    } catch (err) {
      setError(err.message);
      setDeleting(false);
    }
  }

  if (error && !studySet) {
    return (
      <section>
        <p className="error">{error}</p>
        <Link to="/">Back to your study sets</Link>
      </section>
    );
  }
  if (!studySet) return <p className="muted">Loading…</p>;

  const { status } = studySet;

  return (
    <section>
      <p><Link to="/">← Your study sets</Link></p>
      <div className="page-head">
        <h1>{setTitle(studySet)}</h1>
        <span className={`badge badge-${status}`}>{statusLabel(status)}</span>
      </div>

      {error && <p className="error">{error}</p>}

      {!isFinished(status) && (
        <div className="processing" role="status">
          <span className="spinner" aria-hidden="true" />
          <span>{studySet.status_message || "Waiting to start…"}</span>
        </div>
      )}

      {status === "failed" && (
        <div className="notice notice-error">
          <p>{studySet.error || "Processing failed."}</p>
          <button type="button" className="primary" onClick={handleRetry} disabled={retrying}>
            {retrying ? "Retrying…" : "Retry"}
          </button>
        </div>
      )}

      {status === "ready" && (
        <>
          {studySet.overview && <p className="overview">{studySet.overview}</p>}
          <h2>Chapters</h2>
          <ChapterList setId={studySet.id} chapters={studySet.chapters} />
        </>
      )}

      <div className="danger-zone">
        {confirmingDelete ? (
          <>
            <p>Delete this study set, its chapters and its uploaded files? This can't be undone.</p>
            <div className="actions">
              <button type="button" className="danger" onClick={handleDelete} disabled={deleting}>
                {deleting ? "Deleting…" : "Yes, delete"}
              </button>
              <button type="button" onClick={() => setConfirmingDelete(false)} disabled={deleting}>
                Cancel
              </button>
            </div>
          </>
        ) : (
          <button type="button" onClick={() => setConfirmingDelete(true)}>
            Delete study set
          </button>
        )}
      </div>
    </section>
  );
}
