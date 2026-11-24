/*
 LanguageButton.jsx: the header button that switches the interface between English and Greek

 It shows the other language, named in that language ("Ελληνικά" while the interface is English, "English" while it is Greek), 
 so people find their own language even when they can't read the current one, lang= makes screen readers pronounce it right

 the choice is saved with the display settings (display.js): in this browser and in the account when signed in (`account`)
 then the page reloads, so every text is drawn again in the new language, including Clerk's sign-in forms
*/
import { useState } from "react";

import { api } from "../api.js";
import { LANGUAGES, loadDisplay, saveDisplay } from "../display.js";
import { language, t } from "../i18n.js";

export default function LanguageButton({ account = false }) {
  const [switching, setSwitching] = useState(false);
  const other = LANGUAGES.find((l) => l.value !== language);

  async function switchLanguage() {
    setSwitching(true);
    const settings = { ...loadDisplay(), language: other.value };
    saveDisplay(settings);
    if (account) {
      try {
        //waited for, because reloading the page would cancel the request
        await api("/api/display-settings", { method: "PUT", body: settings });
      } catch {
        //not saved to the account (e.g. the server can't be reached), this browser still has it
      }
    }
    window.location.reload();
  }

  return (
    <button type="button" lang={other.value} onClick={switchLanguage} disabled={switching}>
      {/* the screen reader hears ex: "Language: Ελληνικά"; the visible text is just the language */}
      <span className="visually-hidden" lang={language}>{t("nav.language")}: </span>
      {other.label}
    </button>
  );
}
