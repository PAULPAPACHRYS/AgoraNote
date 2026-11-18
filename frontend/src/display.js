// display.js: the display settings (theme, text size, spacing, reading width, motion, links).
//
// They are kept in two places:
// - this browser's localStorage, so they apply straight away on every visit, even on the sign-in screen;
// - the user's account (GET/PUT /api/display-settings), so they follow the user to other browsers and
//   devices. DisplaySettings.jsx loads them from there after signing in and saves every change there.
// They take effect as data-* attributes on <html> (e.g. <html data-theme="dark">), and styles.css does
// the rest, so no component has to know about them.

// Every setting with its choices, in the order the settings panel shows them. The keys and values
// match the API (backend/app/schemas.py, DisplaySettings), which refuses anything else.
export const DISPLAY_SETTINGS = [
  {
    key: "theme",
    label: "Theme",
    choices: [
      { value: "system", label: "Same as my device" }, // follows the operating system's light/dark mode
      { value: "light", label: "Light" },
      { value: "dark", label: "Dark" },
      { value: "contrast", label: "High contrast" },
    ],
  },
  {
    key: "text_size",
    label: "Text size",
    choices: [
      { value: "small", label: "Small" },
      { value: "normal", label: "Normal" },
      { value: "large", label: "Large" },
      { value: "larger", label: "Extra large" },
    ],
  },
  {
    key: "line_spacing",
    label: "Line spacing",
    choices: [
      { value: "normal", label: "Normal" },
      { value: "relaxed", label: "Relaxed" },
      { value: "wide", label: "Wide" },
    ],
  },
  {
    key: "text_spacing",
    label: "Letter and word spacing",
    choices: [
      { value: "normal", label: "Normal" },
      { value: "wider", label: "Wider" },
      { value: "widest", label: "Widest" },
    ],
  },
  {
    key: "reading_width",
    label: "Reading width",
    choices: [
      { value: "narrow", label: "Narrow" },
      { value: "normal", label: "Normal" },
      { value: "wide", label: "Wide" },
    ],
  },
  {
    key: "reduce_motion",
    label: "Reduce motion",
    choices: [
      { value: "system", label: "Same as my device" }, // the operating system's "reduce motion" setting
      { value: "on", label: "On" },
      { value: "off", label: "Off" },
    ],
  },
  {
    key: "underline_links",
    label: "Underline all links",
    choices: [
      { value: "off", label: "Off" },
      { value: "on", label: "On" },
    ],
  },
];

export const DEFAULT_DISPLAY = {
  theme: "system",
  text_size: "normal",
  line_spacing: "normal",
  text_spacing: "normal",
  reading_width: "normal",
  reduce_motion: "system",
  underline_links: "off",
};

const STORAGE_KEY = "agoranote-display";

// Complete, valid settings from `saved`: unknown keys or values are dropped and missing ones get
// their default, so an old or hand-edited entry can't break the page.
export function cleanDisplay(saved) {
  const settings = { ...DEFAULT_DISPLAY };
  for (const setting of DISPLAY_SETTINGS) {
    if (setting.choices.some((c) => c.value === saved?.[setting.key])) {
      settings[setting.key] = saved[setting.key];
    }
  }
  return settings;
}

// The settings saved in this browser, or the defaults. localStorage can throw (e.g. when the browser
// blocks site data), and the saved text might not be valid JSON.
export function loadDisplay() {
  try {
    return cleanDisplay(JSON.parse(localStorage.getItem(STORAGE_KEY)));
  } catch {
    return { ...DEFAULT_DISPLAY };
  }
}

// Put the settings on <html>: text_size becomes the attribute data-text-size, and so on.
export function applyDisplay(settings) {
  for (const [key, value] of Object.entries(settings)) {
    document.documentElement.setAttribute(`data-${key.replaceAll("_", "-")}`, value);
  }
}

// Apply the settings straight away and remember them in this browser for next time.
export function saveDisplay(settings) {
  applyDisplay(settings);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // can't save (blocked site data): the settings still apply until the page is closed
  }
}
