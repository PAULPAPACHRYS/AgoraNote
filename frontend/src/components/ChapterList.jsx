// ChapterList.jsx: the chapter list on the study set page. Every row links to the chapter and shows
// its points bar (with the unlock threshold marked), and a lock note or a "complete" mark.
import { Link } from "react-router-dom";

import ProgressBar from "./ProgressBar.jsx";

// The ordered chapters of a study set, with each chapter's points and whether its quiz is open.
export default function ChapterList({ setId, chapters }) {
  return (
    <ol className="chapter-list">
      {chapters.map((chapter, i) => {
        // The chapter before this one: its points decide whether this chapter's quiz is open.
        const previous = chapters[i - 1];
        return (
          <li key={chapter.id}>
            <Link to={`/sets/${setId}/chapters/${chapter.id}`} className="chapter-row">
              <span className="chapter-number">{chapter.position}</span>
              <span className="chapter-body">
                <span className="chapter-title">{chapter.title}</span>
                <span className="chapter-points">
                  <ProgressBar
                    small
                    value={chapter.earned}
                    max={chapter.max}
                    marker={chapter.unlock_threshold}
                    label={`Chapter ${chapter.position} points`}
                  />
                  <span className="muted small">
                    {chapter.earned} / {chapter.max} pts
                  </span>
                </span>
                {!chapter.quiz_unlocked && previous && (
                  <span className="lock-note small">
                    <span aria-hidden="true">🔒</span> Earn {previous.unlock_threshold - previous.earned} more
                    points in Chapter {previous.position} to unlock this quiz
                  </span>
                )}
                {chapter.completed && <span className="done-note small">✓ Chapter complete</span>}
              </span>
            </Link>
          </li>
        );
      })}
    </ol>
  );
}
