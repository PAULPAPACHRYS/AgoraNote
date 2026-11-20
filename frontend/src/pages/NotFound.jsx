// NotFound.jsx: the "page not found" page, for any URL that matches no route (the "*" route in
// main.jsx). It is shown inside the normal layout, so the header and search box are still there.
import { Link, useLocation } from "react-router-dom";

import { t } from "../i18n.js";

export default function NotFound() {
  const location = useLocation(); // the address that was asked for, shown so typos are easy to spot

  return (
    <section className="empty">
      <h1>{t("notfound.title")}</h1>
      <p>{t("notfound.text", { path: <code>{location.pathname}</code> })}</p>
      <div className="actions">
        <Link to="/" className="button primary">{t("common.back_to_sets")}</Link>
        <Link to="/new" className="button">{t("common.new_set")}</Link>
      </div>
    </section>
  );
}
