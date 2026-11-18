// App.jsx: the layout around every page: the header (app name, search box, display settings and,
// with Clerk, the user menu) and the page itself.
//
// Dev mode: the layout is shown straight away.
// Clerk mode: signed-out visitors see a welcome screen with "Sign in" / "Create an account" (Clerk's
// own sign-in forms open in a pop-up); signed-in users see the app, with Clerk's user menu (profile,
// sign out) at the top right.
import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Show, SignInButton, SignUpButton, UserButton, useAuth } from "@clerk/react";

import { AUTH_MODE, setTokenGetter } from "./auth.js";
import DisplaySettings from "./components/DisplaySettings.jsx";

export default function App() {
  // Clerk's components and hooks only work inside ClerkProvider, which exists only in Clerk mode
  // (see main.jsx), so they are kept in ClerkApp.
  return AUTH_MODE === "clerk" ? <ClerkApp /> : <Layout />;
}

function ClerkApp() {
  const { isLoaded, getToken } = useAuth();
  // Hand Clerk's getToken to api.js. Done during rendering (not in an effect) so it is in place before
  // the pages below start loading data: children's effects run before their parent's effects.
  setTokenGetter(getToken);

  if (!isLoaded) return <p className="muted loading-auth">Loading…</p>; // Clerk is still starting

  return (
    <>
      <Show when="signed-out">
        <SignedOutPage />
      </Show>
      <Show when="signed-in">
        <Layout userMenu={<UserButton />} />
      </Show>
    </>
  );
}

// What a visitor sees before signing in. The buttons are Clerk's: mode="modal" opens Clerk's sign-in
// or sign-up form in a pop-up; our own <button> inside decides how the button looks.
function SignedOutPage() {
  return (
    <div className="app">
      <header className="header">
        <Link to="/" className="brand">AgoraNote</Link>
        <div className="header-end">
          <DisplaySettings />
        </div>
      </header>
      <main className="main">
        <div className="empty">
          <h1>Welcome to AgoraNote</h1>
          <p>
            Upload lecture notes or a lecture recording, or paste some text. AgoraNote splits it into
            chapters and writes a summary, key concepts, practice questions and study aids for each one.
            Then test yourself with chapter quizzes and unlock the next chapter.
          </p>
          <div className="actions">
            <SignInButton mode="modal">
              <button type="button" className="primary">Sign in</button>
            </SignInButton>
            <SignUpButton mode="modal">
              <button type="button">Create an account</button>
            </SignUpButton>
          </div>
        </div>
      </main>
    </div>
  );
}

// The header and the current page. `userMenu` is Clerk's UserButton in Clerk mode, nothing in dev mode.
function Layout({ userMenu = null }) {
  // navigate(url) changes the page from code; location is the current URL.
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState(""); // what is typed in the search box

  // On the results page, keep the box showing what was searched for.
  useEffect(() => {
    if (location.pathname === "/search") {
      setQuery(new URLSearchParams(location.search).get("q") || "");
    }
  }, [location]);

  // Enter in the search box: go to the results page (an empty search does nothing).
  function handleSearch(event) {
    event.preventDefault(); // stop the browser's default form submit (a full page reload)
    if (query.trim()) navigate(`/search?q=${encodeURIComponent(query.trim())}`);
  }

  return (
    <div className="app">
      <header className="header">
        <Link to="/" className="brand">AgoraNote</Link>
        <form className="search-form" role="search" onSubmit={handleSearch}>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search your study sets"
            aria-label="Search your study sets"
            maxLength={200}
          />
        </form>
        <div className="header-end">
          <DisplaySettings />
          {userMenu && <div className="user-menu">{userMenu}</div>}
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
