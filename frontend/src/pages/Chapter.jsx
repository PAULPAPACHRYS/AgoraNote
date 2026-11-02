import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { api } from "../api.js";
import Flashcards from "../components/Flashcards.jsx";
import Quiz from "../components/Quiz.jsx";

const TABS = [
  { id: "summary", label: "Summary" },
  { id: "concepts", label: "Key concepts" },
  { id: "practice", label: "Q&A practice" },
  { id: "aids", label: "Study aids" },
  { id: "quiz", label: "Quiz" },
];

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

function Summary({ paragraphs }) {
  return (
    <div className="prose">
      {paragraphs.map((p, i) => (
        <p key={i}>{p}</p>
      ))}
    </div>
  );
}

function KeyConcepts({ concepts }) {
  return (
    <dl className="concepts">
      {concepts.map((c, i) => (
        <div key={i} className="concept">
          <dt>{c.term}</dt>
          <dd>{c.explanation}</dd>
        </div>
      ))}
    </dl>
  );
}

function StudyAids({ aids }) {
  // Ticks are only for this visit; they aren't saved anywhere.
  const [checked, setChecked] = useState({});

  return (
    <div className="study-aids">
      <section>
        <h2>Outline</h2>
        {aids.outline.map((section, i) => (
          <div key={i} className="outline-section">
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
        <ul className="checklist">
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
        <ul>
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
  const [searchParams, setSearchParams] = useSearchParams();
  const [chapter, setChapter] = useState(null);
  const [error, setError] = useState("");

  // The active tab lives in ?tab= so it can be linked to.
  const tab = TABS.some((t) => t.id === searchParams.get("tab")) ? searchParams.get("tab") : "summary";

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
  const chapterUrl = (other) => `${setUrl}/chapters/${other.id}?tab=${tab}`;

  return (
    <section>
      <p>
        <Link to={setUrl}>← {chapter.study_set_title || "Untitled study set"}</Link>
      </p>
      <p className="muted small chapter-kicker">
        Chapter {chapter.position} of {chapter.chapter_count}
      </p>
      <h1>{chapter.title}</h1>

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`tab ${tab === t.id ? "active" : ""}`}
            onClick={() => setSearchParams({ tab: t.id }, { replace: true })}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="tab-panel" role="tabpanel">
        {tab === "summary" && <Summary paragraphs={chapter.summary} />}
        {tab === "concepts" && <KeyConcepts concepts={chapter.key_concepts} />}
        {tab === "practice" && <Flashcards key={chapter.id} cards={chapter.qa_pairs} />}
        {tab === "aids" && <StudyAids key={chapter.id} aids={chapter.study_aids} />}
        {tab === "quiz" &&
          (chapter.quiz_unlocked ? <Quiz key={chapter.id} chapter={chapter} /> : <QuizLocked chapter={chapter} />)}
      </div>

      <nav className="chapter-nav">
        {chapter.prev_chapter ? (
          <Link to={chapterUrl(chapter.prev_chapter)} className="button">
            ← {chapter.prev_chapter.title}
          </Link>
        ) : (
          <span />
        )}
        {chapter.next_chapter && (
          <Link to={chapterUrl(chapter.next_chapter)} className="button">
            {chapter.next_chapter.title} →
          </Link>
        )}
      </nav>
    </section>
  );
}
