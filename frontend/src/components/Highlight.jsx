// Highlight.jsx: shows a search snippet, turning the server's [[match]] markers into <mark> elements.
// The snippet is plain text, so React escapes everything else: no HTML ever comes from the server.
export default function Highlight({ text }) {
  // split() with a capture group keeps the captured matches at the odd positions.
  // E.g. "a [[cell]] wall" -> ["a ", "cell", " wall"]: index 1 is a match.
  const parts = text.split(/\[\[(.*?)\]\]/s);
  return (
    <span>
      {parts.map((part, i) => (i % 2 === 1 ? <mark key={i}>{part}</mark> : part))}
    </span>
  );
}
