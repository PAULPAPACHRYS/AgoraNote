// api.js: the one place where the frontend talks to the backend.
//
// Every page calls `api(path, options)` instead of `fetch` directly, so these things happen in one
// place for every request: the API's address is prefixed, the login token is attached, JSON is
// encoded and decoded, and errors become JavaScript Errors with a readable message.
//
// Example: const sets = await api("/api/study-sets");
//          await api(`/api/questions/${id}/answer`, { method: "POST", body: { selected_index: 2 } });
import { getToken } from "./auth.js";

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
    throw new Error("Could not reach the server. Is the API running?");
  }

  // Some answers have no body (e.g. 204 after a delete): then `data` is null.
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    // FastAPI errors look like {"detail": "Study set not found."}; show that text to the user.
    const detail = data && data.detail;
    const message = typeof detail === "string" ? detail : `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data;
}
