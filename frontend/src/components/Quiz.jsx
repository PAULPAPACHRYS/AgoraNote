import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api.js";
import ProgressBar from "./ProgressBar.jsx";

const WAIT_POLL_MS = 2000;

// The next question to show: from unmastered topics that have one, starting after the topic
// answered last (so a wrong answer doesn't bring the same topic straight back).
function pickNext(topics, lastTopicId) {
  const open = topics.filter((t) => !t.mastered && t.question);
  if (open.length === 0) return null;
  const lastIndex = topics.findIndex((t) => t.id === lastTopicId);
  return open.find((t) => topics.indexOf(t) > lastIndex) || open[0];
}

export default function Quiz({ chapter }) {
  const [quiz, setQuiz] = useState(null);
  const [error, setError] = useState("");
  const [lastTopicId, setLastTopicId] = useState(null);
  const [answered, setAnswered] = useState(null); // { topic, selected, result } until "Next question"
  const [submitting, setSubmitting] = useState(false);
  const [unlocked, setUnlocked] = useState(null); // the chapter this quiz just unlocked

  function load() {
    return api(`/api/chapters/${chapter.id}/quiz`)
      .then(setQuiz)
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
  }, [chapter.id]);

  const current = answered ? answered.topic : quiz && pickNext(quiz.topics, lastTopicId);
  const allMastered = quiz && quiz.topics.every((t) => t.mastered);
  const waiting = quiz && !current && !allMastered;

  // A replacement question is being generated: check again every 2 s until one is ready.
  useEffect(() => {
    if (!waiting) return;
    const timer = setInterval(load, WAIT_POLL_MS);
    return () => clearInterval(timer);
  }, [waiting]);

  async function choose(index) {
    setError("");
    setSubmitting(true);
    try {
      const result = await api(`/api/questions/${current.question.id}/answer`, {
        method: "POST",
        body: { selected_index: index },
      });
      setAnswered({ topic: current, selected: index, result });
      setLastTopicId(current.id);
      setQuiz({ ...quiz, ...result.chapter, progress: result.progress });
      if (result.unlocked_chapter) setUnlocked(result.unlocked_chapter);
    } catch (err) {
      setError(err.message);
      load(); // e.g. the question was already answered in another tab
    }
    setSubmitting(false);
  }

  function next() {
    setError("");
    setAnswered(null);
    load();
  }

  if (!quiz) return error ? <p className="error">{error}</p> : <p className="muted">Loading quiz…</p>;

  const chapterUrl = (link) => `/sets/${chapter.study_set_id}/chapters/${link.id}?tab=quiz`;
  const { progress } = quiz;

  return (
    <div className="quiz">
      <div className="quiz-points">
        <div className="quiz-points-row">
          <strong>
            Chapter points: {quiz.earned} / {quiz.max}
          </strong>
          {chapter.next_chapter && (
            <span className="muted small">Unlock next chapter at {quiz.unlock_threshold} pts</span>
          )}
        </div>
        <ProgressBar
          value={quiz.earned}
          max={quiz.max}
          marker={chapter.next_chapter ? quiz.unlock_threshold : null}
          label="Chapter points"
        />
        <p className="muted small">
          All chapters: {progress.earned} / {progress.total} points · {progress.percent}%
        </p>
      </div>

      {unlocked && (
        <div className="banner banner-success" role="status">
          <span aria-hidden="true">🔓</span> You unlocked the quiz of <strong>{unlocked.title}</strong>!{" "}
          <Link to={chapterUrl(unlocked)}>Go to that quiz →</Link>
        </div>
      )}

      {error && <p className="error">{error}</p>}

      {current && (
        <div className="question-card">
          <p className="muted small">
            Topic: {current.name} · {current.points} points
          </p>
          <h2 className="question-prompt">{current.question.prompt}</h2>
          <div className="options">
            {current.question.options.map((option, i) => {
              let state = "";
              if (answered) {
                if (i === answered.result.correct_index) state = "correct";
                else if (i === answered.selected) state = "wrong";
              }
              return (
                <button
                  key={i}
                  type="button"
                  className={`option ${state}`}
                  onClick={() => choose(i)}
                  disabled={submitting || !!answered}
                >
                  {option}
                </button>
              );
            })}
          </div>

          {answered && (
            <div className={`feedback ${answered.result.correct ? "feedback-correct" : "feedback-wrong"}`} role="status">
              {answered.result.correct ? (
                <p className="feedback-title">Correct! +{answered.result.points_awarded} points</p>
              ) : (
                <p className="feedback-title">Not quite — the right answer is highlighted.</p>
              )}
              <p>{answered.result.explanation}</p>
              {answered.result.replacement_pending && (
                <p className="small">
                  A new question on <em>{current.name}</em> is being prepared.
                </p>
              )}
              <button type="button" className="primary" onClick={next}>
                Next question
              </button>
            </div>
          )}
        </div>
      )}

      {waiting && (
        <div className="processing" role="status">
          <span className="spinner" aria-hidden="true" />
          <span>Preparing your next question…</span>
        </div>
      )}

      {allMastered && !answered && (
        <div className="banner banner-success">
          <p className="feedback-title">Chapter complete!</p>
          <p>You mastered every topic in this chapter.</p>
          {chapter.next_chapter ? (
            <Link to={chapterUrl(chapter.next_chapter)} className="button primary">
              Next chapter: {chapter.next_chapter.title} →
            </Link>
          ) : (
            <Link to={`/sets/${chapter.study_set_id}`} className="button primary">
              Back to the study set
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
