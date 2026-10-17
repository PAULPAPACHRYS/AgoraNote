import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api.js";
import { setTitle, statusLabel } from "../status.js";

export default function StudySet() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [studySet, setStudySet] = useState(null);
  const [error, setError] = useState("");
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    api(`/api/study-sets/${id}`)
      .then(setStudySet)
      .catch((err) => setError(err.message));
  }, [id]);

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

  return (
    <section>
      <p><Link to="/">← Your study sets</Link></p>
      <div className="page-head">
        <h1>{setTitle(studySet)}</h1>
        <span className={`badge badge-${studySet.status}`}>{statusLabel(studySet.status)}</span>
      </div>
      {studySet.status_message && <p className="muted">{studySet.status_message}</p>}
      {studySet.error && <p className="error">{studySet.error}</p>}

      {error && <p className="error">{error}</p>}

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
