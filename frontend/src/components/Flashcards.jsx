// Flashcards.jsx: the "Q&A practice" tab of a chapter.
import { useEffect, useState } from "react";

import { t } from "../i18n.js";

// Q&A practice: question on the front; click, tap or Space reveals the answer. No points here.
// `lang` is the material's language: it goes on the card's text, not on the interface's labels.
export default function Flashcards({ cards, lang }) {
  const [index, setIndex] = useState(0); // which card is shown
  const [revealed, setRevealed] = useState(false); // showing the answer side?

  // Space anywhere on the page flips the card. When a button has focus, the browser already
  // turns Space into a click on that button, so we leave those alone.
  useEffect(() => {
    function onKeyDown(event) {
      if (event.key !== " " || event.target.closest("button, input, textarea, select, a")) return;
      event.preventDefault(); // don't scroll the page
      setRevealed((r) => !r);
    }
    window.addEventListener("keydown", onKeyDown);
    // Remove the listener again when the flashcards disappear (e.g. another tab is opened).
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  if (cards.length === 0) return <p className="muted">{t("flashcards.none")}</p>;

  // Previous (-1) / next (+1) card; a new card always starts on the question side.
  function go(step) {
    setIndex((i) => i + step);
    setRevealed(false);
  }

  const card = cards[index];

  return (
    <div className="flashcards">
      <button
        type="button"
        className={`flashcard ${revealed ? "revealed" : ""}`}
        onClick={() => setRevealed((r) => !r)}
      >
        <span className="flashcard-label">{revealed ? t("flashcards.answer") : t("flashcards.question")}</span>
        <span className="flashcard-text" lang={lang}>{revealed ? card.answer : card.question}</span>
        <span className="flashcard-hint muted small">
          {revealed ? t("flashcards.hint_back") : t("flashcards.hint_reveal")}
        </span>
      </button>

      <div className="flashcard-nav">
        <button type="button" onClick={() => go(-1)} disabled={index === 0}>
          {t("flashcards.previous")}
        </button>
        <span className="muted">{t("flashcards.card", { n: index + 1, total: cards.length })}</span>
        <button type="button" onClick={() => go(1)} disabled={index === cards.length - 1}>
          {t("flashcards.next")}
        </button>
      </div>
    </div>
  );
}
