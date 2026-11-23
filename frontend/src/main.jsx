/*
 main.jsx: the entry point of the browser app (loaded by index.html)

 it defines the routes (which page is shown for which URL) and puts the app into the page
 every page is a child of <App />, which draws the header and shows the current page in its <Outlet /> 
`:id` and `:chapterId` are URL parameters, read in the pages with useParams()
*/
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { ClerkProvider } from "@clerk/react";
import { elGR } from "@clerk/localizations";

import App from "./App.jsx";
import { AUTH_MODE } from "./auth.js";
import { applyDisplay, loadDisplay } from "./display.js";
import { language } from "./i18n.js";
import Chapter from "./pages/Chapter.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import ErrorPage from "./pages/ErrorPage.jsx";
import NewStudySet from "./pages/NewStudySet.jsx";
import NotFound from "./pages/NotFound.jsx";
import Privacy from "./pages/Privacy.jsx";
import Search from "./pages/Search.jsx";
import StudySet from "./pages/StudySet.jsx";
import "./styles.css";

// apply the saved display settings (theme, text size, ..., and the language as <html lang>) before the first page is drawn
applyDisplay(loadDisplay());

/*
 errorElement: what React Router shows instead of a route whose page crashed 
 The inner one (on a route without a path, which only groups the pages) keeps the header around the error page 
 the outer one catches errors in App/the layout itself
 "*" matches any URL no other route matches
*/
const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    errorElement: <ErrorPage standalone />,
    children: [
      {
        errorElement: <ErrorPage />,
        children: [
          { index: true, element: <Dashboard /> },
          { path: "new", element: <NewStudySet /> },
          { path: "sets/:id", element: <StudySet /> },
          { path: "sets/:id/chapters/:chapterId", element: <Chapter /> },
          { path: "search", element: <Search /> },
          { path: "privacy", element: <Privacy /> }, //also open to signed-out visitors (App.jsx)
          { path: "*", element: <NotFound /> },
        ],
      },
    ],
  },
]);

const app = <RouterProvider router={router} />;
/*
 StrictMode is a development helper: it runs effects twice to reveal bugs so in development you
 may see each request twice in the network tab, production builds don't do that
 
 In Clerk mode the whole app sits inside ClerkProvider, which loads Clerk, keeps track of the signed-in
 user and makes Clerk's components and hooks (used in App.jsx) work
 
 the publishable key only identifies our Clerk instance, it is not a secret
 afterSignOutUrl: where to go after signing out
 localization: Clerk's own texts (sign-in forms, account menu) in Greek when the interface is Greek, without it Clerk uses English
*/
createRoot(document.getElementById("root")).render(
  <StrictMode>
    {AUTH_MODE === "clerk" ? (
      <ClerkProvider
        publishableKey={import.meta.env.VITE_CLERK_PUBLISHABLE_KEY}
        afterSignOutUrl="/"
        localization={language === "el" ? elGR : undefined}
      >
        {app}
      </ClerkProvider>
    ) : (
      app
    )}
  </StrictMode>
);
