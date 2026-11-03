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

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
