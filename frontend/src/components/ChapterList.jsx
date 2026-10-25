// The ordered chapters of a study set. Links, points and locks are added in later phases.
export default function ChapterList({ chapters }) {
  return (
    <ol className="chapter-list">
      {chapters.map((chapter) => (
        <li key={chapter.id} className="chapter-row">
          <span className="chapter-number">{chapter.position}</span>
          <span className="chapter-title">{chapter.title}</span>
        </li>
      ))}
    </ol>
  );
}
