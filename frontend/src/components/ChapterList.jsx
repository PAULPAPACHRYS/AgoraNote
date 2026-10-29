import { Link } from "react-router-dom";

// The ordered chapters of a study set. Points and locks are added with the quiz (Phase 4).
export default function ChapterList({ setId, chapters }) {
  return (
    <ol className="chapter-list">
      {chapters.map((chapter) => (
        <li key={chapter.id}>
          <Link to={`/sets/${setId}/chapters/${chapter.id}`} className="chapter-row">
            <span className="chapter-number">{chapter.position}</span>
            <span className="chapter-title">{chapter.title}</span>
          </Link>
        </li>
      ))}
    </ol>
  );
}
