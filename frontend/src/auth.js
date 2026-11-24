/*
 auth.js: where the login token comes from

 VITE_AUTH_MODE (read at build time, see .env.example):
 - "dev":   no login, no token is sent and the backend uses one fixed development user
 - "clerk": users sign in with Clerk, every API request carries a fresh Clerk session token
*/
export const AUTH_MODE = import.meta.env.VITE_AUTH_MODE || "dev";

/*
 Clerk's getToken function can only be obtained inside React components (with the useAuth hook),
 but api.js is plain JavaScript, so App.jsx hands it over with setTokenGetter, and getToken below calls it
*/
let tokenGetter = null;

export function setTokenGetter(getter) {
  tokenGetter = getter;
}

/*
 returns the current user's session token or null (dev mode, or not signed in)
 Clerk tokens live for about a minute, Clerk's getToken returns a cached token while it is
 still valid and fetches a fresh one when needed, so it is called before every request
*/
export async function getToken() {
  return tokenGetter ? tokenGetter() : null;
}
