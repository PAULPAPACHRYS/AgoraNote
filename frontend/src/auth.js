// Returns the current user's auth token, or null in dev mode (the backend then uses a fixed dev user).
// The real provider's token getter is plugged in here in Phase 8.
export async function getToken() {
  return null;
}
