"""Getting plain text out of uploaded files, and cutting it into blocks for the LLM."""
import re

import docx
import pypdf
from pypdf.errors import FileNotDecryptedError, PyPdfError


class ProcessingError(Exception):
    """A problem with the user's material. The message is shown to the user as-is."""


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)  # at most one blank line between paragraphs
    return text.strip()


def extract_text(path: str, filename: str) -> str:
    """Plain text of a .txt, .md, .pdf or .docx file."""
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext in ("txt", "md"):
        with open(path, encoding="utf-8", errors="replace") as f:
            return clean_text(f.read())
    if ext == "pdf":
        return clean_text(_pdf_text(path, filename))
    if ext == "docx":
        paragraphs = [p.text for p in docx.Document(path).paragraphs if p.text.strip()]
        return clean_text("\n\n".join(paragraphs))
    raise ProcessingError(f'"{filename}" is not a text document.')


def _pdf_text(path: str, filename: str) -> str:
    try:
        reader = pypdf.PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
    except FileNotDecryptedError:
        raise ProcessingError(f'"{filename}" is password-protected. Please upload an unprotected PDF.')
    except PyPdfError:
        raise ProcessingError(f'"{filename}" could not be read. Is it a valid PDF?')
    text = "\n\n".join(pages)
    # Scanned PDFs are just images: pypdf finds (almost) no text in them.
    if len(text.strip()) < 20 * max(1, len(pages)):
        raise ProcessingError(
            f'"{filename}": This PDF looks like scanned images; only text-based PDFs are supported for now.'
        )
    return text


# --- splitting text into blocks ---------------------------------------------------------------

BLOCK_CHARS = 1000

# Sentence ends: . ! ? … and ; which is also the Greek question mark (plus its own code point U+037E).
_SENTENCE_END = re.compile(r"(?<=[.!?…;;])\s+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]


def _hard_wrap(text: str, size: int) -> list[str]:
    """Cut an over-long 'sentence' (e.g. an unpunctuated transcript) at word boundaries."""
    if len(text) <= size:
        return [text]
    pieces, current = [], ""
    for word in text.split():
        if current and len(current) + 1 + len(word) > size:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        pieces.append(current)
    return pieces


def split_into_blocks(text: str, size: int = BLOCK_CHARS) -> list[str]:
    """Cut text into blocks of about `size` characters at paragraph or sentence boundaries.

    Transcripts have no paragraphs, so long paragraphs are cut at sentence ends instead.
    """
    # Each piece remembers how it joins the previous one: a paragraph break or a space.
    pieces = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= size:
            pieces.append(("\n\n", paragraph))
            continue
        joiner = "\n\n"
        for sentence in split_sentences(paragraph):
            for piece in _hard_wrap(sentence, size):
                pieces.append((joiner, piece))
                joiner = " "

    blocks, current = [], ""
    for joiner, piece in pieces:
        if current and len(current) + len(joiner) + len(piece) > size:
            blocks.append(current)
            current = piece
        else:
            current = current + joiner + piece if current else piece
    if current:
        blocks.append(current)
    return blocks
