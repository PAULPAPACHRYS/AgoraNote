// display.js: the display settings (theme, text size, line spacing).
//
// They are saved in this browser's localStorage, so they survive a reload and already apply on the
// sign-in screen. They belong to the browser, not to the account: another browser starts with the
// defaults. They take effect as data-* attributes on <html> (e.g. <html data-theme="dark">), and
// styles.css does the rest, so no component has to know about them.

// Every setting with its choices, in the order the settings panel shows them.
export const DISPLAY_SETTINGS = [
  {
    key: "theme",
    label: "Theme",
    choices: [
      { value: "system", label: "Same as my device" }, // follows the operating system's light/dark mode
      { value: "light", label: "Light" },
      { value: "dark", label: "Dark" },
    ],
  },
  {
    key: "textSize",
    label: "Text size",
    choices: [
      { value: "small", label: "Small" },
      { value: "normal", label: "Normal" },
      { value: "large", label: "Large" },
      { value: "larger", label: "Extra large" },
    ],
  },
  {
    key: "lineSpacing",
    label: "Line spacing",
    choices: [
      { value: "normal", label: "Normal" },
      { value: "relaxed", label: "Relaxed" },
      { value: "wide", label: "Wide" },
    ],
  },
];

export const DEFAULT_DISPLAY = { theme: "system", textSize: "normal", lineSpacing: "normal" };

const STORAGE_KEY = "agoranote-display";

// The saved settings, or the defaults. Unknown keys or values are ignored, so an old or hand-edited
// entry can't break the page. localStorage can throw (e.g. when the browser blocks site data).
export function loadDisplay() {
  const settings = { ...DEFAULT_DISPLAY };
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    for (const setting of DISPLAY_SETTINGS) {
      if (setting.choices.some((c) => c.value === saved[setting.key])) {
        settings[setting.key] = saved[setting.key];
      }
    }
  } catch {
    // nothing saved that we can read: keep the defaults
  }
  return settings;
}

// Put the settings on <html>: dataset.textSize becomes the attribute data-text-size, and so on.
export function applyDisplay(settings) {
  const root = document.documentElement;
  root.dataset.theme = settings.theme;
  root.dataset.textSize = settings.textSize;
  root.dataset.lineSpacing = settings.lineSpacing;
}

// Apply the settings straight away and remember them for next time.
export function saveDisplay(settings) {
  applyDisplay(settings);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // can't save (blocked site data): the settings still apply until the page is closed
  }
}
