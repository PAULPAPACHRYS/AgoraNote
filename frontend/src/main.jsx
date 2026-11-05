// main.jsx: the entry point of the browser app (loaded by index.html).
//
// It defines the routes (which page is shown for which URL) and puts the app into the page.
// Every page is a child of <App />, which draws the header and shows the current page in its
// <Outlet />. `:id` and `:chapterId` are URL parameters, read in the pages with useParams().
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import App from "./App.jsx";
import Chapter from "./pages/Chapter.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import NewStudySet from "./pages/NewStudySet.jsx";
import Search from "./pages/Search.jsx";
import StudySet from "./pages/StudySet.jsx";
import "./styles.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "new", element: <NewStudySet /> },
      { path: "sets/:id", element: <StudySet /> },
      { path: "sets/:id/chapters/:chapterId", element: <Chapter /> },
      { path: "search", element: <Search /> },
    ],
  },
]);

// StrictMode is a development helper: it runs effects twice to reveal bugs (so in development you
// may see each request twice in the network tab; production builds don't do that).
createRoot(document.getElementById("root")).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
