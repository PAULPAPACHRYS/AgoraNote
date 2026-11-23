/*
 App.jsx: the layout around every page: the header which includes app name, search box,  
 language button, display settings and with Clerk the user menu
 
 the page itself and the footer (privacy link)

 Dev mode: 
 -the layout is shown straight away
 
 Clerk mode: 
  -signed-out visitors see a welcome screen with "Sign in" / "Create an account" (Clerk's own sign-in forms)
  -signed-in users see the app, with Clerk's user menu (profile, sign out) at the top right
*/
import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Show, SignInButton, SignUpButton, UserButton, useAuth } from "@clerk/react";

import { AUTH_MODE, setTokenGetter } from "./auth.js";
import DisplaySettings from "./components/DisplaySettings.jsx";
import LanguageButton from "./components/LanguageButton.jsx";
import { t } from "./i18n.js";

export default function App() {
  // Clerk's components and hooks only work inside ClerkProvider, 
  //which exists only in Clerk mode (see main.jsx), so they are kept in ClerkApp
  return AUTH_MODE === "clerk" ? <ClerkApp /> : <Layout />;
}

function ClerkApp() {
  const { isLoaded, getToken } = useAuth();
  // hand Clerk's getToken to api.js, done during rendering (not in an effect) so it is in place before
  // the pages below start loading data: children's effects run before their parent's effects
  setTokenGetter(getToken);

  if (!isLoaded) return <p className="muted loading-auth">{t("common.loading")}</p>; // Clerk is still starting

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
/*
 what a visitor sees before signing in
 buttons are Clerk's: mode="modal" opens Clerk's sign-in
 or sign-up form in a pop-up, our own <button> inside decides how the button looks
 the privacy page is the one page open to signed-out visitors, so it can be read before signing up
*/
function SignedOutPage() {
  const location = useLocation();
  const publicPage = location.pathname === "/privacy";

  return (
    <div className="app">
      <header className="header">
        <Link to="/" className="brand">AgoraNote</Link>
        <div className="header-end">
          <LanguageButton />
          <DisplaySettings />
        </div>
      </header>
      <main className="main">
        {publicPage ? <Outlet /> : <Welcome />}
      </main>
      <Footer />
    </div>
  );
}

function Welcome() {
  return (
    <div className="empty">
      <h1>{t("welcome.title")}</h1>
      <p>
        {t("welcome.intro")} {t("welcome.quizzes_short")}
      </p>
      <div className="actions">
        <SignInButton mode="modal">
          <button type="button" className="primary">{t("welcome.sign_in")}</button>
        </SignInButton>
        <SignUpButton mode="modal">
          <button type="button">{t("welcome.sign_up")}</button>
        </SignUpButton>
      </div>
    </div>
  );
}

// header and the current page, `userMenu` is Clerk's UserButton in Clerk mode
function Layout({ userMenu = null }) {
  //navigate(url) changes the page from code, location is the current URL
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState(""); //what is typed in the search box

  // on the results page, keep the box showing what was searched for
  useEffect(() => {
    if (location.pathname === "/search") {
      setQuery(new URLSearchParams(location.search).get("q") || "");
    }
  }, [location]);

  // enter in the search box: go to the results page (an empty search does nothing)
  function handleSearch(event) {
    event.preventDefault(); //stop the browser's default form submit (a full page reload)
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
            placeholder={t("nav.search")}
            aria-label={t("nav.search")}
            maxLength={200}
          />
        </form>
        <div className="header-end">
          {/* account: also save the choices to the signed-in user's account */}
          <LanguageButton account />
          <DisplaySettings account />
          {userMenu && <div className="user-menu">{userMenu}</div>}
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}

// at the bottom of every page, signed in or not
function Footer() {
  return (
    <footer className="footer">
      <Link to="/privacy">{t("nav.privacy")}</Link>
    </footer>
  );
}
