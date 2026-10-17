import { Link, Outlet } from "react-router-dom";

export default function App() {
  return (
    <div className="app">
      <header className="header">
        <Link to="/" className="brand">AgoraNote</Link>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
