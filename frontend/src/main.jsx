// main.jsx: the entry point of the browser app (loaded by index.html).
//
// It defines the routes (which page is shown for which URL) and puts the app into the page.
// Every page is a child of <App />, which draws the header and shows the current page in its
// <Outlet />. `:id` and `:chapterId` are URL parameters, read in the pages with useParams().
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { ClerkProvider } from "@clerk/react";

import App from "./App.jsx";
import { AUTH_MODE } from "./auth.js";
import { applyDisplay, loadDisplay } from "./display.js";
import Chapter from "./pages/Chapter.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import ErrorPage from "./pages/ErrorPage.jsx";
import NewStudySet from "./pages/NewStudySet.jsx";
import NotFound from "./pages/NotFound.jsx";
import Search from "./pages/Search.jsx";
import StudySet from "./pages/StudySet.jsx";
import "./styles.css";

// Apply the saved display settings (theme, text size, line spacing) before the first page is drawn.
applyDisplay(loadDisplay());

// errorElement: what React Router shows instead of a route whose page crashed. The inner one (on a
// route without a path, which only groups the pages) keeps the header around the error page; the
// outer one catches errors in App/the layout itself. "*" matches any URL no other route matches.
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
          { path: "*", element: <NotFound /> },
        ],
      },
    ],
  },
]);

const app = <RouterProvider router={router} />;

// StrictMode is a development helper: it runs effects twice to reveal bugs (so in development you
// may see each request twice in the network tab; production builds don't do that).
// In Clerk mode the whole app sits inside ClerkProvider, which loads Clerk, keeps track of the signed-in
// user and makes Clerk's components and hooks (used in App.jsx) work. The publishable key only
// identifies our Clerk instance; it is not a secret. afterSignOutUrl: where to go after signing out.
createRoot(document.getElementById("root")).render(
  <StrictMode>
    {AUTH_MODE === "clerk" ? (
      <ClerkProvider publishableKey={import.meta.env.VITE_CLERK_PUBLISHABLE_KEY} afterSignOutUrl="/">
        {app}
      </ClerkProvider>
    ) : (
      app
    )}
  </StrictMode>
);
