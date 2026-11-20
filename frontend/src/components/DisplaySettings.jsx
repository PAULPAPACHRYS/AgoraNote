// DisplaySettings.jsx: the "Display settings" button in the header and the panel it opens, with the
// settings listed in display.js. A change applies straight away and is saved in this browser.
//
// With `account` (when signed in), the settings are also saved to the user's account: on opening the
// app the account's settings replace this browser's (they may come from another device), and every
// change is sent to the API. When the account has none saved yet, the browser's settings stay.
// The interface language is saved with these settings (see LanguageButton.jsx): when the account's
// language differs from this browser's, the page reloads to show it.
//
// It follows the WAI-ARIA "disclosure" pattern: the button says whether the panel is open
// (aria-expanded) and which element it opens (aria-controls). The panel comes right after the button,
// so Tab moves into it. Escape or a click outside closes it; Escape and "Done" put the focus back on
// the button. The choices are radio buttons, so the arrow keys move between them.
import { useEffect, useState } from "react";

import { api } from "../api.js";
import { cleanDisplay, DEFAULT_DISPLAY, DISPLAY_SETTINGS, loadDisplay, saveDisplay } from "../display.js";
import { language, t } from "../i18n.js";

export default function DisplaySettings({ account = false }) {
  const [open, setOpen] = useState(false);
  const [settings, setSettings] = useState(loadDisplay); // this browser's settings (or the defaults)
  const [saveError, setSaveError] = useState("");

  // Signed in: load the settings saved in the account. null = none saved yet.
  useEffect(() => {
    if (!account) return;
    api("/api/display-settings")
      .then((saved) => {
        if (!saved) return;
        // anything the account doesn't have yet (e.g. no language chosen) keeps this browser's value
        const fromAccount = cleanDisplay(saved, loadDisplay());
        setSettings(fromAccount);
        saveDisplay(fromAccount);
        // Another language: reload to draw everything in it. Only when it was really saved in this
        // browser (it may block site data), else the reload would load the old language again, forever.
        if (fromAccount.language !== language && loadDisplay().language === fromAccount.language) {
          window.location.reload();
        }
      })
      .catch(() => {}); // e.g. the server can't be reached: keep this browser's settings
  }, [account]);

  // Apply and save new settings: always in this browser, and in the account when signed in.
  function update(next) {
    setSettings(next);
    saveDisplay(next);
    if (!account) return;
    setSaveError("");
    api("/api/display-settings", { method: "PUT", body: next }).catch(() =>
      setSaveError(t("display.save_error"))
    );
  }

  function change(key, value) {
    update({ ...settings, [key]: value });
  }

  // The language isn't one of the panel's settings, so it stays.
  function reset() {
    update({ ...DEFAULT_DISPLAY, language: settings.language });
  }

  function close() {
    setOpen(false);
    document.getElementById("display-settings-button").focus();
  }

  // While the panel is open, a click anywhere outside it closes it, like a menu.
  useEffect(() => {
    if (!open) return;
    function handleMouseDown(event) {
      if (!event.target.closest(".display-settings")) setOpen(false);
    }
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown); // stop listening when closed
  }, [open]);

  function handleKeyDown(event) {
    if (event.key === "Escape" && open) close();
  }

  return (
    <div className="display-settings" onKeyDown={handleKeyDown}>
      <button
        id="display-settings-button"
        type="button"
        aria-expanded={open}
        aria-controls="display-settings-panel"
        onClick={() => setOpen(!open)}
      >
        {t("display.button")}
      </button>

      {/* Always in the page (hidden when closed), so aria-controls points at a real element. */}
      <div id="display-settings-panel" className="display-panel" hidden={!open}>
        {DISPLAY_SETTINGS.map((setting) => (
          <fieldset key={setting.key}>
            <legend>{t(`display.${setting.key}`)}</legend>
            <div className="choices">
              {setting.choices.map((choice) => (
                <label key={choice} className="choice">
                  <input
                    type="radio"
                    name={`display-${setting.key}`}
                    value={choice}
                    checked={settings[setting.key] === choice}
                    onChange={() => change(setting.key, choice)}
                  />
                  {t(`display.${setting.key}.${choice}`)}
                </label>
              ))}
            </div>
          </fieldset>
        ))}
        {saveError && (
          <p className="error small" role="alert">
            {saveError}
          </p>
        )}
        <div className="actions">
          <button type="button" onClick={reset}>
            {t("display.reset")}
          </button>
          <button type="button" className="primary" onClick={close}>
            {t("display.done")}
          </button>
        </div>
      </div>
    </div>
  );
}
