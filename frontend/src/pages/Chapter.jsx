// Chapter.jsx: one chapter ("/sets/:id/chapters/:chapterId") with five tabs:
// Summary, Key concepts, Q&A practice (flashcards), Study aids and Quiz (or a "locked" notice).
// The active tab is kept in the URL (?tab=quiz), so a link can open a chapter on a specific tab.
//
// The tabs follow the WAI-ARIA "tabs" pattern (https://www.w3.org/WAI/ARIA/apg/patterns/tabs/):
// only the active tab is in the Tab key order; the arrow keys move between tabs and open them
// straight away, Home/End jump to the first/last tab. Every tab names its panel (aria-controls)
// and every panel names its tab (aria-labelledby), so screen readers announce which tab is open.
//
// The interface is English, but the generated content is in the material's language: those
// elements get lang={chapter.language} (e.g. "el") so screen readers pronounce them correctly.
import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { api } from "../api.js";
import Flashcards from "../components/Flashcards.jsx";
import Quiz from "../components/Quiz.jsx";

// The tabs in display order: `id` is what appears in ?tab=, `label` is the button text.
const TABS = [
  { id: "summary", label: "Summary" },
  { id: "concepts", label: "Key concepts" },
  { id: "practice", label: "Q&A practice" },
  { id: "aids", label: "Study aids" },
  { id: "quiz", label: "Quiz" },
];

// Shown on the Quiz tab while this chapter's quiz is locked: what to do to unlock it.
function QuizLocked({ chapter }) {
  return (
    <div className="locked">
      <p className="locked-title">
        <span aria-hidden="true">🔒</span> This quiz is locked
      </p>
      <p>
        Earn {chapter.points_to_unlock} more points in Chapter {chapter.position - 1} to unlock this quiz.
        The study materials in the other tabs are always open.
      </p>
      {chapter.prev_chapter && (
        <Link to={`/sets/${chapter.study_set_id}/chapters/${chapter.prev_chapter.id}?tab=quiz`}>
          Go to the Chapter {chapter.position - 1} quiz →
        </Link>
      )}
    </div>
  );
}

// "Summary" tab: the summary paragraphs.
// (key={i}: React needs a key per list item; the index is fine for lists that never reorder.)
function Summary({ paragraphs, lang }) {
  return (
    <div className="prose" lang={lang}>
      {paragraphs.map((p, i) => (
        <p key={i}>{p}</p>
      ))}
    </div>
  );
}

// "Key concepts" tab: a definition list of term + explanation.
function KeyConcepts({ concepts, lang }) {
  return (
    <dl className="concepts" lang={lang}>
      {concepts.map((c, i) => (
        <div key={i} className="concept">
          <dt>{c.term}</dt>
          <dd>{c.explanation}</dd>
        </div>
      ))}
    </dl>
  );
}

// "Study aids" tab: the outline, a review checklist with tick boxes, and memory tips.
// The section headings are interface text (English); `lang` goes on the generated parts only.
function StudyAids({ aids, lang }) {
  // Ticks are only for this visit; they aren't saved anywhere.
  const [checked, setChecked] = useState({}); // item index -> ticked?

  return (
    <div className="study-aids">
      <section>
        <h2>Outline</h2>
        {aids.outline.map((section, i) => (
          <div key={i} className="outline-section" lang={lang}>
            <h3>{section.heading}</h3>
            <ul>
              {section.points.map((point, j) => (
                <li key={j}>{point}</li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <section>
        <h2>Review checklist</h2>
        <ul className="checklist" lang={lang}>
          {aids.review_checklist.map((item, i) => (
            <li key={i}>
              <label>
                <input
                  type="checkbox"
                  checked={!!checked[i]}
                  onChange={(e) => setChecked({ ...checked, [i]: e.target.checked })}
                />
                <span>{item}</span>
              </label>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Memory tips</h2>
        <ul lang={lang}>
          {aids.memory_tips.map((tip, i) => (
            <li key={i}>{tip}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export default function Chapter() {
  const { chapterId } = useParams();
  // searchParams = the ?tab=... part of the URL; setSearchParams changes it (and so the tab).
  const [searchParams, setSearchParams] = useSearchParams();
  const [chapter, setChapter] = useState(null);
  const [error, setError] = useState("");

  // The active tab lives in ?tab= so it can be linked to.
  const tab = TABS.some((t) => t.id === searchParams.get("tab")) ? searchParams.get("tab") : "summary";

  // Load the chapter whenever the chapter in the URL changes (also via the prev/next links).
  useEffect(() => {
    setChapter(null);
    setError("");
    api(`/api/chapters/${chapterId}`)
      .then(setChapter)
      .catch((err) => setError(err.message));
  }, [chapterId]);

  if (error) {
    return (
      <section>
        <p className="error">{error}</p>
        <Link to="/">Back to your study sets</Link>
      </section>
    );
  }
  if (!chapter) return <p className="muted">Loading…</p>;

  const setUrl = `/sets/${chapter.study_set_id}`;
  // Previous/next chapter links open the same tab the user is on now.
  const chapterUrl = (other) => `${setUrl}/chapters/${other.id}?tab=${tab}`;
  const lang = chapter.language; // e.g. "el"; null = unknown (React then leaves the attribute out)

  // Open a tab by putting it in the URL (replace: switching tabs doesn't add browser history).
  function openTab(id) {
    setSearchParams({ tab: id }, { replace: true });
  }

  // Keyboard support of the tab row: the arrow keys open the previous/next tab (wrapping around at
  // the ends), Home/End the first/last one, and focus moves along to the tab that was opened.
  function handleTabKeyDown(event) {
    const index = TABS.findIndex((t) => t.id === tab);
    const target = {
      ArrowLeft: (index - 1 + TABS.length) % TABS.length,
      ArrowRight: (index + 1) % TABS.length,
      Home: 0,
      End: TABS.length - 1,
    }[event.key];
    if (target === undefined) return; // any other key: leave it to the browser
    event.preventDefault(); // e.g. stop Home/End from also scrolling the page
    openTab(TABS[target].id);
    document.getElementById(`tab-${TABS[target].id}`).focus();
  }

  // The content of the active tab. key={chapter.id} gives each chapter fresh flashcard and
  // checklist state instead of carrying it over from the previous chapter.
  let content;
  if (tab === "summary") content = <Summary paragraphs={chapter.summary} lang={lang} />;
  else if (tab === "concepts") content = <KeyConcepts concepts={chapter.key_concepts} lang={lang} />;
  else if (tab === "practice") content = <Flashcards key={chapter.id} cards={chapter.qa_pairs} lang={lang} />;
  else if (tab === "aids") content = <StudyAids key={chapter.id} aids={chapter.study_aids} lang={lang} />;
  else content = chapter.quiz_unlocked ? <Quiz key={chapter.id} chapter={chapter} /> : <QuizLocked chapter={chapter} />;

  return (
    <section>
      <p>
        <Link to={setUrl}>
          ←{" "}
          {chapter.study_set_title ? <span lang={lang}>{chapter.study_set_title}</span> : "Untitled study set"}
        </Link>
      </p>
      <p className="muted small chapter-kicker">
        Chapter {chapter.position} of {chapter.chapter_count}
      </p>
      <h1 lang={lang}>{chapter.title}</h1>

      {/* Only the active tab has tabIndex 0, so Tab jumps from the tab row straight into the panel;
          the other tabs are reached with the arrow keys. */}
      <div className="tabs" role="tablist" aria-label="Chapter materials" onKeyDown={handleTabKeyDown}>
        {TABS.map((t) => (
          <button
            key={t.id}
            id={`tab-${t.id}`}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            aria-controls={`panel-${t.id}`}
            tabIndex={tab === t.id ? 0 : -1}
            className={`tab ${tab === t.id ? "active" : ""}`}
            onClick={() => openTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* One panel per tab, so every tab's aria-controls points at a real element. Only the active
          panel is visible and filled; the others are empty and hidden. tabIndex={0} lets keyboard
          users reach a panel that has nothing focusable in it (e.g. the summary). */}
      {TABS.map((t) => (
        <div
          key={t.id}
          id={`panel-${t.id}`}
          className="tab-panel"
          role="tabpanel"
          aria-labelledby={`tab-${t.id}`}
          tabIndex={0}
          hidden={tab !== t.id}
        >
          {tab === t.id && content}
        </div>
      ))}

      <nav className="chapter-nav">
        {chapter.prev_chapter ? (
          <Link to={chapterUrl(chapter.prev_chapter)} className="button">
            ← <span lang={lang}>{chapter.prev_chapter.title}</span>
          </Link>
        ) : (
          <span />
        )}
        {chapter.next_chapter && (
          <Link to={chapterUrl(chapter.next_chapter)} className="button">
            <span lang={lang}>{chapter.next_chapter.title}</span> →
          </Link>
        )}
      </nav>
    </section>
  );
}
