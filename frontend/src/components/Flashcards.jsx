// Flashcards.jsx: the "Q&A practice" tab of a chapter
import { useEffect, useState } from "react";

import { t } from "../i18n.js";

// Q&A practice: question on the front: click, tap or Space reveals the answer
// `lang` is the material's language: it goes on the card's text, not on the interface's labels
export default function Flashcards({ cards, lang }) {
  const [index, setIndex] = useState(0); //which card is shown
  const [revealed, setRevealed] = useState(false); //showing the answer side?

  // space anywhere on the page flips the card
  // when a button has focus, the browser already turns space into a click on that button
  useEffect(() => {
    function onKeyDown(event) {
      if (event.key !== " " || event.target.closest("button, input, textarea, select, a")) return;
      event.preventDefault(); // don't scroll the page
      setRevealed((r) => !r);
    }
    window.addEventListener("keydown", onKeyDown);
    // remove the listener again when the flashcards disappear (ex: another tab is opened)
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  if (cards.length === 0) return <p className="muted">{t("flashcards.none")}</p>;

  // previous (-1) / next (+1) card, a new card always starts on the question side
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
