/*
 display.js: the display settings (theme, text size, spacing, reading width, motion, links) and the interface language

 they are kept in two places:
 - this browser's localStorage, so they apply straight away on every visit, even on the sign-in screen
 - the user's account (GET/PUT /api/display-settings), so they follow the user to other browsers and devices

 DisplaySettings.jsx loads them from there after signing in and saves every change there
 they take effect as data-* attributes on <html> (e.g. <html data-theme="dark">) and styles.css does
 the rest, so no component has to know about them, the language becomes <html lang="...">

 every setting of the settings panel with its choices, in the order the panel shows them 
 their labels are in i18n.js ("display.theme", "display.theme.dark", ...) 
 keys and values match the API (backend/app/schemas.py, DisplaySettings), which refuses anything else
*/
export const DISPLAY_SETTINGS = [
  { key: "theme", choices: ["system", "light", "dark", "contrast"] }, //system = the device's light/dark mode
  { key: "text_size", choices: ["small", "normal", "large", "larger"] },
  { key: "line_spacing", choices: ["normal", "relaxed", "wide"] },
  { key: "text_spacing", choices: ["normal", "wider", "widest"] }, // letter and word spacing
  { key: "reading_width", choices: ["narrow", "normal", "wide"] },
  { key: "reduce_motion", choices: ["system", "on", "off"] }, //system = the device's "reduce motion"
  { key: "underline_links", choices: ["off", "on"] },
];

// the interface languages, each named in its own language, 
// language button in the header (LanguageButton.jsx) switches between them, the choice is saved with the display settings
export const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "el", label: "Ελληνικά" },
];

// first visit: Greek when the browser's preferred language is Greek, otherwise English
function browserLanguage() {
  return (navigator.language || "").toLowerCase().startsWith("el") ? "el" : "en";
}

export const DEFAULT_DISPLAY = {
  theme: "system",
  text_size: "normal",
  line_spacing: "normal",
  text_spacing: "normal",
  reading_width: "normal",
  reduce_motion: "system",
  underline_links: "off",
  language: browserLanguage(),
};

const STORAGE_KEY = "agoranote-display";

// complete, valid settings from `saved`: unknown keys or values are dropped and missing ones are
// taken from `base` (normally the defaults), so an old or edited entry can't break the page
export function cleanDisplay(saved, base = DEFAULT_DISPLAY) {
  const settings = { ...base };
  for (const setting of DISPLAY_SETTINGS) {
    if (setting.choices.includes(saved?.[setting.key])) settings[setting.key] = saved[setting.key];
  }
  if (LANGUAGES.some((l) => l.value === saved?.language)) settings.language = saved.language;
  return settings;
}

//settings saved in this browser or the defaults, 
// localStorage can throw (ex: when the browser blocks site data) and the saved text might not be valid JSON
export function loadDisplay() {
  try {
    return cleanDisplay(JSON.parse(localStorage.getItem(STORAGE_KEY)));
  } catch {
    return { ...DEFAULT_DISPLAY };
  }
}

// put the settings on <html>: text_size becomes the attribute data-text-size, and so on
// language becomes the lang attribute, which tells screen readers and the browser which language the page is in
export function applyDisplay(settings) {
  for (const [key, value] of Object.entries(settings)) {
    if (key === "language") document.documentElement.lang = value;
    else document.documentElement.setAttribute(`data-${key.replaceAll("_", "-")}`, value);
  }
}

// apply the settings straight away and remember them in this browser for next time
export function saveDisplay(settings) {
  applyDisplay(settings);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    //can't save (blocked site data): the settings still apply until the page is closed
  }
}
