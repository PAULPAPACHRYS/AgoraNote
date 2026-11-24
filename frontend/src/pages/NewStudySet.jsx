/*
 NewStudySet.jsx: the upload form ("/new"): optional title, files and/or pasted text
 
 after a successful upload it goes straight to the new set's page, which shows the progress
 above the form: the daily limit, how many new sets are left or when the next one is possible
*/
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import DailyLimit from "../components/DailyLimit.jsx";
import { language, t } from "../i18n.js";

// same as server defaults (MAX_FILES_PER_SET, MAX_FILE_MB),  server enforces the real limits
const MAX_FILES = 5;
const MAX_FILE_MB = 200;
// Which files the file picker offers (the server checks again).
const ACCEPT = ".txt,.md,.pdf,.docx,.mp3,.m4a,.wav,.ogg,.webm,.mp4";

// 1234567 -> "1.2 MB" ("1,2 MB" in Greek), 2048 -> "2 KB"
function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toLocaleString(language, { maximumFractionDigits: 1 })} MB`;
}

export default function NewStudySet() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [files, setFiles] = useState([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false); //disables the buttons while uploading
  const [usage, setUsage] = useState(null); //daily limit, null = not loaded

  // ask how many new sets are left, If that fails the form still works: the server checks the limit anyway
  function loadUsage() {
    api("/api/study-sets/usage").then(setUsage).catch(() => setUsage(null));
  }

  useEffect(() => {
    loadUsage();
  }, []); //once, when the page opens

  const limitReached = !!(usage && usage.next_free_at);

  // quick checks before uploading, so obvious mistakes don't need a round trip
  // Returns an error message, or "" when everything is fine, texts are the same as the server's for these checks
  function checkInput() {
    if (files.length === 0 && !text.trim()) return t("message.nothing_uploaded");
    if (files.length > MAX_FILES) return t("message.too_many_files", { max: MAX_FILES });
    const tooBig = files.find((f) => f.size > MAX_FILE_MB * 1024 * 1024);
    if (tooBig) return t("message.file_too_large", { filename: tooBig.name, max_mb: MAX_FILE_MB });
    return "";
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const problem = checkInput();
    if (problem) {
      setError(problem);
      return;
    }

    // a multipart form, like a classic HTML form with file fields: the format the API expects
    // each file is appended under the same name "files", the server receives them as a list
    const form = new FormData();
    if (title.trim()) form.append("title", title.trim());
    if (text.trim()) form.append("text", text);
    files.forEach((f) => form.append("files", f));

    setError("");
    setSubmitting(true);
    try {
      const created = await api("/api/study-sets", { method: "POST", body: form });
      navigate(`/sets/${created.id}`); //processing continues in the background
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
      loadUsage(); //ex: the limit was reached in another tab: show when the next set is possible
    }
  }

  return (
    <section>
      <h1>{t("common.new_set")}</h1>
      <DailyLimit usage={usage} />
      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          <span>{t("new.title_label")}</span>
          <input
            type="text"
            value={title}
            maxLength={200}
            placeholder={t("new.title_placeholder")}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>

        <label className="field">
          <span>{t("new.files")}</span>
          <input
            type="file"
            multiple
            accept={ACCEPT}
            onChange={(e) => setFiles(Array.from(e.target.files))}
          />
          <span className="muted small">{t("new.files_help", { max: MAX_FILES, max_mb: MAX_FILE_MB })}</span>
        </label>

        {files.length > 0 && (
          <ul className="file-list">
            {files.map((f) => (
              <li key={f.name + f.size}>
                {f.name} <span className="muted small">({formatSize(f.size)})</span>
              </li>
            ))}
          </ul>
        )}

        <label className="field">
          <span>{t("new.text")}</span>
          <textarea rows={10} value={text} onChange={(e) => setText(e.target.value)} />
        </label>

        {error && <p className="error">{error}</p>}

        <div className="actions">
          <button type="submit" className="primary" disabled={submitting || limitReached}>
            {submitting ? t("new.uploading") : t("new.create")}
          </button>
          <button type="button" onClick={() => navigate("/")} disabled={submitting}>
            {t("common.cancel")}
          </button>
        </div>
      </form>
    </section>
  );
}
