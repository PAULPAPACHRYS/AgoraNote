/*
 StudySet.jsx: one study set ("/sets/:id")
 while the set is processed it shows the live status (polled every 3 s)
 when it failed, the error and a Retry button
 when ready, the overview, the overall points and the chapter list
*/
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, isNotFound } from "../api.js";
import ChapterList from "../components/ChapterList.jsx";
import ProgressBar from "../components/ProgressBar.jsx";
import { messageText, t } from "../i18n.js";
import { setTitle, statusLabel, titleLang } from "../status.js";
import NotFound from "./NotFound.jsx";

const POLL_MS = 3000; //how often to ask for the status while processing

// no more polling needed once processing has ended, successfully or not
function isFinished(status) {
  return status === "ready" || status === "failed";
}

export default function StudySet() {
  const { id } = useParams(); // the id part of the URL
  const navigate = useNavigate();
  const [studySet, setStudySet] = useState(null);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false); // no such set (or not this user's): show the 404 page
  const [pollKey, setPollKey] = useState(0); // bumped by Retry to start polling again
  const [retrying, setRetrying] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false); // two step delete: ask first
  const [deleting, setDeleting] = useState(false);

  // load the set, then keep polling while it is being processed
  useEffect(() => {
    let timer = null;
    setNotFound(false); //new id: forget that the previous one didn't exist
    function load() {
      api(`/api/study-sets/${id}`)
        .then((data) => {
          setStudySet(data);
          setError("");
          if (isFinished(data.status)) clearInterval(timer);
        })
        .catch((err) => {
          if (isNotFound(err)) {
            setNotFound(true); //also when the set is deleted (ex: in another tab) while polling
            clearInterval(timer);
          } else {
            setError(err.message);
          }
        });
    }
    load();
    timer = setInterval(load, POLL_MS);
    // React calls this cleanup when the page closes (or id/pollKey change): stop the timer
    return () => clearInterval(timer);
  }, [id, pollKey]);

  // Retry: the server resets the set to "queued" and starts processing again, polling restarts
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

  // second step of deleting (after "Delete study set" -> "Yes, delete"), then back to the dashboard
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

  if (notFound) return <NotFound />;
  // couldn't load at all (ex: the server can't be reached): show only the error
  if (error && !studySet) {
    return (
      <section>
        <p className="error">{error}</p>
        <Link to="/">{t("common.back_to_sets")}</Link>
      </section>
    );
  }
  if (!studySet) return <p className="muted">{t("common.loading")}</p>;

  const { status } = studySet;

  return (
    <section>
      <p><Link to="/">{t("set.back")}</Link></p>
      <div className="page-head">
        <h1 lang={titleLang(studySet)}>{setTitle(studySet)}</h1>
        <span className={`badge badge-${status}`}>{statusLabel(status)}</span>
      </div>

      {error && <p className="error">{error}</p>}

      {!isFinished(status) && (
        <div className="processing" role="status">
          <span className="spinner" aria-hidden="true" />
          {/* status_message: the step as a message code plus values, ex: "generating_chapter" 2 of 5 */}
          <span>{studySet.status_message ? messageText(studySet.status_message) : t("set.waiting")}</span>
        </div>
      )}

      {status === "failed" && (
        <div className="notice notice-error">
          <p>{studySet.error ? messageText(studySet.error) : t("set.failed")}</p>
          <button type="button" className="primary" onClick={handleRetry} disabled={retrying}>
            {retrying ? t("set.retrying") : t("set.retry")}
          </button>
        </div>
      )}

      {status === "ready" && (
        <>
          {/* lang: the overview and chapter titles are in the material's language (ex: "el") */}
          {studySet.overview && <p className="overview" lang={studySet.language}>{studySet.overview}</p>}
          <div className="overall-progress">
            <ProgressBar
              value={studySet.progress.earned}
              max={studySet.progress.total}
              label={t("set.overall_progress")}
            />
            <p>
              <strong>{t("set.points", { earned: studySet.progress.earned, total: studySet.progress.total })}</strong>{" "}
              · {studySet.progress.percent}%
            </p>
          </div>
          <h2>{t("common.chapters")}</h2>
          <ChapterList setId={studySet.id} chapters={studySet.chapters} lang={studySet.language} />
        </>
      )}

      <div className="danger-zone">
        {confirmingDelete ? (
          <>
            <p>{t("set.delete_confirm")}</p>
            <div className="actions">
              <button type="button" className="danger" onClick={handleDelete} disabled={deleting}>
                {deleting ? t("set.deleting") : t("set.delete_yes")}
              </button>
              <button type="button" onClick={() => setConfirmingDelete(false)} disabled={deleting}>
                {t("common.cancel")}
              </button>
            </div>
          </>
        ) : (
          <button type="button" onClick={() => setConfirmingDelete(true)}>
            {t("set.delete")}
          </button>
        )}
      </div>
    </section>
  );
}
