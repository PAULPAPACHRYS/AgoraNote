// api.js: the one place where the frontend talks to the backend.
//
// Every page calls `api(path, options)` instead of `fetch` directly, so these things happen in one
// place for every request: the API's address is prefixed, the login token is attached, JSON is
// encoded and decoded, and errors become JavaScript Errors with a readable message in the interface
// language.
//
// Example: const sets = await api("/api/study-sets");
//          await api(`/api/questions/${id}/answer`, { method: "POST", body: { selected_index: 2 } });
import { getToken } from "./auth.js";
import { messageText, t } from "./i18n.js";

// Read at build time from the VITE_API_URL environment variable (see .env.example).
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// The one way the frontend talks to the backend. Throws an Error carrying the API's `detail`.
export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };

  // Ask for a fresh token on every request; provider tokens are short-lived.
  const token = await getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  // JSON bodies are serialised here; FormData (uploads) is passed through untouched.
  let body = options.body;
  if (body && !(body instanceof FormData) && typeof body !== "string") {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }

  // fetch only throws when the server can't be reached at all (not for 4xx/5xx answers).
  let response;
  try {
    response = await fetch(API_URL + path, { ...options, headers, body });
  } catch {
    throw new Error(t("error.no_server"));
  }

  // Some answers have no body (e.g. 204 after a delete): then `data` is null.
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    // Our API's errors carry a message code plus values, e.g.
    // {"detail": {"code": "study_set_not_found", "values": {}}}, shown in the interface language.
    // Others (e.g. FastAPI's own 422 answers) get a general text with the status code.
    const detail = data && data.detail;
    const message = detail && detail.code ? messageText(detail) : t("error.request_failed", { status: response.status });
    const error = new Error(message);
    error.status = response.status; // e.g. 404, so a page can tell "doesn't exist" from other errors
    throw error;
  }
  return data;
}

// True when a page's thing doesn't exist (or belongs to someone else, which the API also answers
// with 404), so the page shows the "Page not found" page. 422 is FastAPI's answer to an id that
// isn't a number at all (e.g. /sets/abc), which doesn't exist either.
export function isNotFound(error) {
  return error.status === 404 || error.status === 422;
}
