// Quiz.jsx: the "Quiz" tab of a chapter.
//
// How it works: load the quiz state (every topic and its current question) -> show one question ->
// on a click, send the answer to the server, which grades it -> show the feedback (correct answer,
// explanation, points) -> "Next question" reloads the state and shows the next open topic.
// A wrong answer makes the server prepare a new question on that topic in the background; when no
// question is available yet, the quiz shows "Preparing your next question…" and checks every 2 s.
// Generated text (topics, questions, answers, explanations, chapter titles) gets lang={lang}, the
// material's language; the quiz's own labels are in the interface language (i18n.js).
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api.js";
import { t } from "../i18n.js";
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
  const [quiz, setQuiz] = useState(null); // the quiz state from GET /api/chapters/{id}/quiz
  const [error, setError] = useState("");
  const [lastTopicId, setLastTopicId] = useState(null); // the topic answered last
  const [answered, setAnswered] = useState(null); // { topic, selected, result } until "Next question"
  const [submitting, setSubmitting] = useState(false);
  const [unlocked, setUnlocked] = useState(null); // the chapter this quiz just unlocked

  // (Re)load the quiz state from the server.
  function load() {
    return api(`/api/chapters/${chapter.id}/quiz`)
      .then(setQuiz)
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
  }, [chapter.id]);

  // These are worked out on every render from the state above:
  // the topic on screen (the answered one while its feedback shows, else the next open one),
  const current = answered ? answered.topic : quiz && pickNext(quiz.topics, lastTopicId);
  // whether the chapter is finished, and whether we are waiting for a replacement question.
  const allMastered = quiz && quiz.topics.every((t) => t.mastered);
  const waiting = quiz && !current && !allMastered;

  // A replacement question is being generated: check again every 2 s until one is ready.
  useEffect(() => {
    if (!waiting) return;
    const timer = setInterval(load, WAIT_POLL_MS);
    return () => clearInterval(timer);
  }, [waiting]);

  // An option was clicked: send it to the server, which grades it.
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
      // Update the points bars right away with the new totals from the answer.
      setQuiz({ ...quiz, ...result.chapter, progress: result.progress });
      if (result.unlocked_chapter) setUnlocked(result.unlocked_chapter);
    } catch (err) {
      setError(err.message);
      load(); // e.g. the question was already answered in another tab
    }
    setSubmitting(false);
  }

  // "Next question": leave the feedback and fetch fresh state (a replacement may be ready by now).
  function next() {
    setError("");
    setAnswered(null);
    load();
  }

  if (!quiz) return error ? <p className="error">{error}</p> : <p className="muted">{t("quiz.loading")}</p>;

  const chapterUrl = (link) => `/sets/${chapter.study_set_id}/chapters/${link.id}?tab=quiz`;
  const { progress } = quiz;
  const lang = chapter.language; // e.g. "el"; null = unknown (no lang attribute)

  return (
    <div className="quiz">
      <div className="quiz-points">
        <div className="quiz-points-row">
          <strong>{t("quiz.chapter_points_value", { earned: quiz.earned, max: quiz.max })}</strong>
          {chapter.next_chapter && (
            <span className="muted small">{t("quiz.unlock_at", { n: quiz.unlock_threshold })}</span>
          )}
        </div>
        <ProgressBar
          value={quiz.earned}
          max={quiz.max}
          marker={chapter.next_chapter ? quiz.unlock_threshold : null}
          label={t("quiz.chapter_points")}
        />
        <p className="muted small">
          {t("quiz.all_chapters", { earned: progress.earned, total: progress.total, percent: progress.percent })}
        </p>
      </div>

      {unlocked && (
        <div className="banner banner-success" role="status">
          <span aria-hidden="true">🔓</span>{" "}
          {t("quiz.unlocked", { title: <strong lang={lang}>{unlocked.title}</strong> })}{" "}
          <Link to={chapterUrl(unlocked)}>{t("quiz.unlocked_link")}</Link>
        </div>
      )}

      {error && <p className="error">{error}</p>}

      {current && (
        <div className="question-card">
          <p className="muted small">
            {t("quiz.topic", { name: <span lang={lang}>{current.name}</span>, count: current.points })}
          </p>
          <h2 className="question-prompt" lang={lang}>{current.question.prompt}</h2>
          <div className="options" lang={lang}>
            {current.question.options.map((option, i) => {
              // After answering: the correct option turns green, a wrong pick red.
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
                <p className="feedback-title">{t("quiz.correct", { count: answered.result.points_awarded })}</p>
              ) : (
                <p className="feedback-title">{t("quiz.wrong")}</p>
              )}
              <p lang={lang}>{answered.result.explanation}</p>
              {answered.result.replacement_pending && (
                <p className="small">
                  {t("quiz.replacement", { topic: <em lang={lang}>{current.name}</em> })}
                </p>
              )}
              <button type="button" className="primary" onClick={next}>
                {t("quiz.next_question")}
              </button>
            </div>
          )}
        </div>
      )}

      {waiting && (
        <div className="processing" role="status">
          <span className="spinner" aria-hidden="true" />
          <span>{t("quiz.preparing")}</span>
        </div>
      )}

      {allMastered && !answered && (
        <div className="banner banner-success">
          <p className="feedback-title">{t("quiz.complete")}</p>
          <p>{t("quiz.mastered")}</p>
          {chapter.next_chapter ? (
            <Link to={chapterUrl(chapter.next_chapter)} className="button primary">
              {t("quiz.next_chapter", { title: <span lang={lang}>{chapter.next_chapter.title}</span> })}
            </Link>
          ) : (
            <Link to={`/sets/${chapter.study_set_id}`} className="button primary">
              {t("quiz.back_to_set")}
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
