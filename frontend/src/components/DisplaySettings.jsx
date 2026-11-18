// DisplaySettings.jsx: the "Display settings" button in the header and the panel it opens, with the
// theme, text size and line spacing (see display.js). A change applies straight away and is saved.
//
// It follows the WAI-ARIA "disclosure" pattern: the button says whether the panel is open
// (aria-expanded) and which element it opens (aria-controls). The panel comes right after the button,
// so Tab moves into it. Escape or a click outside closes it; Escape and "Done" put the focus back on
// the button. The choices are radio buttons, so the arrow keys move between them.
import { useEffect, useState } from "react";

import { DEFAULT_DISPLAY, DISPLAY_SETTINGS, loadDisplay, saveDisplay } from "../display.js";

export default function DisplaySettings() {
  const [open, setOpen] = useState(false);
  const [settings, setSettings] = useState(loadDisplay); // the saved settings (or the defaults)

  function change(key, value) {
    const next = { ...settings, [key]: value };
    setSettings(next);
    saveDisplay(next);
  }

  function reset() {
    setSettings(DEFAULT_DISPLAY);
    saveDisplay(DEFAULT_DISPLAY);
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
        Display settings
      </button>

      {/* Always in the page (hidden when closed), so aria-controls points at a real element. */}
      <div id="display-settings-panel" className="display-panel" hidden={!open}>
        {DISPLAY_SETTINGS.map((setting) => (
          <fieldset key={setting.key}>
            <legend>{setting.label}</legend>
            <div className="choices">
              {setting.choices.map((choice) => (
                <label key={choice.value} className="choice">
                  <input
                    type="radio"
                    name={`display-${setting.key}`}
                    value={choice.value}
                    checked={settings[setting.key] === choice.value}
                    onChange={() => change(setting.key, choice.value)}
                  />
                  {choice.label}
                </label>
              ))}
            </div>
          </fieldset>
        ))}
        <div className="actions">
          <button type="button" onClick={reset}>
            Reset to defaults
          </button>
          <button type="button" className="primary" onClick={close}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
