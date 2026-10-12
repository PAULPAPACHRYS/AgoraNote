import { getToken } from "./auth.js";

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

  let response;
  try {
    response = await fetch(API_URL + path, { ...options, headers, body });
  } catch {
    throw new Error("Could not reach the server. Is the API running?");
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data && data.detail;
    const message = typeof detail === "string" ? detail : `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data;
}
