// Chapter.jsx: one chapter ("/sets/:id/chapters/:chapterId") with five tabs:
// Summary, Key concepts, Q&A practice (flashcards), Study aids and Quiz (or a "locked" notice).
// The active tab is kept in the URL (?tab=quiz), so a link can open a chapter on a specific tab.
//
// The tabs follow the WAI-ARIA "tabs" pattern (https://www.w3.org/WAI/ARIA/apg/patterns/tabs/):
// only the active tab is in the Tab key order; the arrow keys move between tabs and open them
// straight away, Home/End jump to the first/last tab. Every tab names its panel (aria-controls)
// and every panel names its tab (aria-labelledby), so screen readers announce which tab is open.
//
// The interface is in the chosen language (i18n.js), the generated content in the material's language:
// those elements get lang={chapter.language} (e.g. "el") so screen readers pronounce them correctly.
import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { api, isNotFound } from "../api.js";
import Flashcards from "../components/Flashcards.jsx";
import Quiz from "../components/Quiz.jsx";
import { t } from "../i18n.js";
import NotFound from "./NotFound.jsx";

// The tabs in display order: `id` is what appears in ?tab=; the button text is t("chapter.tab.<id>").
const TABS = [{ id: "summary" }, { id: "concepts" }, { id: "practice" }, { id: "aids" }, { id: "quiz" }];

// Shown on the Quiz tab while this chapter's quiz is locked: what to do to unlock it.
function QuizLocked({ chapter }) {
  return (
    <div className="locked">
      <p className="locked-title">
        <span aria-hidden="true">🔒</span> {t("chapter.locked")}
      </p>
      <p>
        {t("chapter.unlock_hint", { count: chapter.points_to_unlock, chapter: chapter.position - 1 })}{" "}
        {t("chapter.locked_other_tabs")}
      </p>
      {chapter.prev_chapter && (
        <Link to={`/sets/${chapter.study_set_id}/chapters/${chapter.prev_chapter.id}?tab=quiz`}>
          {t("chapter.locked_link", { n: chapter.position - 1 })}
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
// The section headings are interface text; `lang` goes on the generated parts only.
function StudyAids({ aids, lang }) {
  // Ticks are only for this visit; they aren't saved anywhere.
  const [checked, setChecked] = useState({}); // item index -> ticked?

  return (
    <div className="study-aids">
      <section>
        <h2>{t("chapter.outline")}</h2>
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
        <h2>{t("chapter.checklist")}</h2>
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
        <h2>{t("chapter.memory_tips")}</h2>
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
  const [notFound, setNotFound] = useState(false); // no such chapter (or not this user's): 404 page

  // The active tab lives in ?tab= so it can be linked to.
  const tab = TABS.some((item) => item.id === searchParams.get("tab")) ? searchParams.get("tab") : "summary";

  // Load the chapter whenever the chapter in the URL changes (also via the prev/next links).
  useEffect(() => {
    setChapter(null);
    setError("");
    setNotFound(false);
    api(`/api/chapters/${chapterId}`)
      .then(setChapter)
      .catch((err) => (isNotFound(err) ? setNotFound(true) : setError(err.message)));
  }, [chapterId]);

  if (notFound) return <NotFound />;
  if (error) {
    return (
      <section>
        <p className="error">{error}</p>
        <Link to="/">{t("common.back_to_sets")}</Link>
      </section>
    );
  }
  if (!chapter) return <p className="muted">{t("common.loading")}</p>;

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
    const index = TABS.findIndex((item) => item.id === tab);
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
          {chapter.study_set_title ? <span lang={lang}>{chapter.study_set_title}</span> : t("common.untitled_set")}
        </Link>
      </p>
      <p className="muted small chapter-kicker">
        {t("chapter.of", { n: chapter.position, total: chapter.chapter_count })}
      </p>
      <h1 lang={lang}>{chapter.title}</h1>

      {/* Only the active tab has tabIndex 0, so Tab jumps from the tab row straight into the panel;
          the other tabs are reached with the arrow keys. */}
      <div className="tabs" role="tablist" aria-label={t("chapter.tabs")} onKeyDown={handleTabKeyDown}>
        {TABS.map((item) => (
          <button
            key={item.id}
            id={`tab-${item.id}`}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            aria-controls={`panel-${item.id}`}
            tabIndex={tab === item.id ? 0 : -1}
            className={`tab ${tab === item.id ? "active" : ""}`}
            onClick={() => openTab(item.id)}
          >
            {t(`chapter.tab.${item.id}`)}
          </button>
        ))}
      </div>

      {/* One panel per tab, so every tab's aria-controls points at a real element. Only the active
          panel is visible and filled; the others are empty and hidden. tabIndex={0} lets keyboard
          users reach a panel that has nothing focusable in it (e.g. the summary). */}
      {TABS.map((item) => (
        <div
          key={item.id}
          id={`panel-${item.id}`}
          className="tab-panel"
          role="tabpanel"
          aria-labelledby={`tab-${item.id}`}
          tabIndex={0}
          hidden={tab !== item.id}
        >
          {tab === item.id && content}
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
