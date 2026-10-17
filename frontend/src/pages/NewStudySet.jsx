import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api.js";

// Mirrors the server defaults (MAX_FILES_PER_SET, MAX_FILE_MB). The server enforces the real limits.
const MAX_FILES = 5;
const MAX_FILE_MB = 200;
const ACCEPT = ".txt,.md,.pdf,.docx,.mp3,.m4a,.wav,.ogg,.webm,.mp4";

function formatSize(bytes) {
  return bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function NewStudySet() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [files, setFiles] = useState([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function checkInput() {
    if (files.length === 0 && !text.trim()) return "Choose at least one file or paste some text.";
    if (files.length > MAX_FILES) return `You can upload at most ${MAX_FILES} files.`;
    const tooBig = files.find((f) => f.size > MAX_FILE_MB * 1024 * 1024);
    if (tooBig) return `"${tooBig.name}" is larger than ${MAX_FILE_MB} MB.`;
    return "";
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const problem = checkInput();
    if (problem) {
      setError(problem);
      return;
    }

    const form = new FormData();
    if (title.trim()) form.append("title", title.trim());
    if (text.trim()) form.append("text", text);
    files.forEach((f) => form.append("files", f));

    setError("");
    setSubmitting(true);
    try {
      const created = await api("/api/study-sets", { method: "POST", body: form });
      navigate(`/sets/${created.id}`);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <section>
      <h1>New study set</h1>
      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Title (optional)</span>
          <input
            type="text"
            value={title}
            maxLength={200}
            placeholder="Leave empty to generate one from the material"
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>

        <label className="field">
          <span>Files</span>
          <input
            type="file"
            multiple
            accept={ACCEPT}
            onChange={(e) => setFiles(Array.from(e.target.files))}
          />
          <span className="muted small">
            Text: .txt, .md, .pdf, .docx · Audio/video: .mp3, .m4a, .wav, .ogg, .webm, .mp4 · Up to{" "}
            {MAX_FILES} files, {MAX_FILE_MB} MB each.
          </span>
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
          <span>…and/or paste text</span>
          <textarea rows={10} value={text} onChange={(e) => setText(e.target.value)} />
        </label>

        {error && <p className="error">{error}</p>}

        <div className="actions">
          <button type="submit" className="primary" disabled={submitting}>
            {submitting ? "Uploading…" : "Create study set"}
          </button>
          <button type="button" onClick={() => navigate("/")} disabled={submitting}>
            Cancel
          </button>
        </div>
      </form>
    </section>
  );
}
