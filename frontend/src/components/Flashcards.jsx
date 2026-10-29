import { useEffect, useState } from "react";

// Q&A practice: question on the front; click, tap or Space reveals the answer. No points here.
export default function Flashcards({ cards }) {
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);

  // Space anywhere on the page flips the card. When a button has focus, the browser already
  // turns Space into a click on that button, so we leave those alone.
  useEffect(() => {
    function onKeyDown(event) {
      if (event.key !== " " || event.target.closest("button, input, textarea, select, a")) return;
      event.preventDefault(); // don't scroll the page
      setRevealed((r) => !r);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  if (cards.length === 0) return <p className="muted">No practice questions for this chapter.</p>;

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
        <span className="flashcard-label">{revealed ? "Answer" : "Question"}</span>
        <span className="flashcard-text">{revealed ? card.answer : card.question}</span>
        <span className="flashcard-hint muted small">
          {revealed ? "Click or press Space to see the question" : "Click or press Space to reveal the answer"}
        </span>
      </button>

      <div className="flashcard-nav">
        <button type="button" onClick={() => go(-1)} disabled={index === 0}>
          ← Previous
        </button>
        <span className="muted">
          Card {index + 1} of {cards.length}
        </span>
        <button type="button" onClick={() => go(1)} disabled={index === cards.length - 1}>
          Next →
        </button>
      </div>
    </div>
  );
}
