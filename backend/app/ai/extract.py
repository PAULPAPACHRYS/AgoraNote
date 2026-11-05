"""
Getting text out of uploaded files, preparing audio for transcription, and cutting text into blocks

Three parts:
1. **Documents** (extract_text): .txt/.md are read directly, .pdf with pypdf, .docx with python-docx
   PDF page headers/footers are removed (strip_repeated_lines)
2. **Blocks** (split_into_blocks): the combined text is cut into ~1,000-character blocks at paragraph
   or sentence boundaries. The LLM decides chapter boundaries in terms of these numbered blocks
3. **Audio/video** (prepare_audio): ffmpeg converts a recording into small MP3 segments for Whisper

problems with the user's material raise ProcessingError, whose message is shown to the user
"""
import glob
import os
import re
import subprocess
from collections import Counter

import docx
import pypdf
from pypdf.errors import FileNotDecryptedError, PyPdfError


class ProcessingError(Exception):
    #problem with the user's material, The message is shown to the user
    pass


def clean_text(text: str) -> str:
    #normalise line endings and whitespace: Windows/old-Mac newlines -> "\n", no trailing spaces
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)  # at most one blank line between paragraphs
    return text.strip()


def extract_text(path: str, filename: str) -> str:
    """
    Plain text of a .txt, .md, .pdf or .docx file
    `path` is the local copy to read; `filename` is the user's original name (for the extension and
    for error messages)
    """
    ext = filename.lower().rsplit(".", 1)[-1]  # "Notes.PDF" -> "pdf"
    if ext in ("txt", "md"):
        # errors="replace": a file that isn't valid UTF-8 still opens; bad bytes become "?"-like marks
        with open(path, encoding="utf-8", errors="replace") as f:
            return clean_text(f.read())
    if ext == "pdf":
        return clean_text(_pdf_text(path, filename))
    if ext == "docx":
        # word paragraphs, skipping empty ones. (Tables, headers and footers are not read.)
        paragraphs = [p.text for p in docx.Document(path).paragraphs if p.text.strip()]
        return clean_text("\n\n".join(paragraphs))
    raise ProcessingError(f'"{filename}" is not a text document.')


def _line_key(line: str) -> str:
    #line in a form for comparing: whitespace collapsed, every number replaced by "#"
    # numbers become "#" so "Page 3 of 30" and "Page 4 of 30" count as the same line
    return re.sub(r"\d+", "#", " ".join(line.split()))


def strip_repeated_lines(pages: list[str]) -> list[str]:
    """
    remove page headers and footers: lines found on at least half of the pages, and bare page numbers
    slides repeat the course code, date or lecturer's name on every page; left in, they end up in chapter titles and summaries
    """
    if len(pages) < 3:  # too few pages to tell a header from real content
        return pages
    # how many pages does each line appear? (a set per page: a line counts once per page)
    counts = Counter(key for page in pages for key in {_line_key(line) for line in page.splitlines() if line.strip()})
    repeated = {key for key, n in counts.items() if n >= len(pages) / 2}
    return [
        "\n".join(
            line for line in page.splitlines()
            if _line_key(line) not in repeated and not line.strip().isdigit()
        )
        for page in pages
    ]


def _pdf_text(path: str, filename: str) -> str:
    # text of every page of a PDF, headers/footers removed, pages separated by a blank line
    try:
        reader = pypdf.PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
    except FileNotDecryptedError:
        raise ProcessingError(f'"{filename}" is password-protected. Please upload an unprotected PDF.')
    except PyPdfError:
        raise ProcessingError(f'"{filename}" could not be read. Is it a valid PDF?')
    text = "\n\n".join(strip_repeated_lines(pages))
    # Scanned PDFs are just images: pypdf finds (almost) no text in them.
    if len(text.strip()) < 20 * max(1, len(pages)):
        raise ProcessingError(
            f'"{filename}": This PDF looks like scanned images; only text-based PDFs are supported for now.'
        )
    return text


# --- splitting text into blocks ---------------------------------------------------------------

BLOCK_CHARS = 1000  # target size of one block, in characters

# sentence ends: . ! ? … and ; which is also the Greek question mark (plus its own code point U+037E)
_SENTENCE_END = re.compile(r"(?<=[.!?…;;])\s+")


def split_sentences(text: str) -> list[str]:
    #split text after sentence-ending punctuation followed by whitespace, empty pieces dropped
    return [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]


def _hard_wrap(text: str, size: int) -> list[str]:
    # cut an over-long 'sentence' (e.g. an unpunctuated transcript) at word boundaries
    if len(text) <= size:
        return [text]
    # add words to the current piece until the next word would make it too long, then start a new one
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
    """
    cut text into blocks of about `size` characters at paragraph or sentence boundaries
    transcripts have no paragraphs, so long paragraphs are cut at sentence ends instead

    each piece remembers how it joins the previous one: a paragraph break or a space
    step 1: cut the text into pieces of at most `size` characters: whole paragraphs where they fit,
    otherwise sentences (and over-long sentences at word boundaries)
    """
    pieces = []
    for paragraph in re.split(r"\n\s*\n", text):  # paragraphs are separated by blank lines
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

    # step 2: glue consecutive pieces together until adding the next one would exceed `size`
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


# --- audio and video ------------------------------------------------------------------------------

# 10-minute segments of mono 16 kHz MP3 at 32 kbit/s are ~2.4 MB and 16 kHz mono, what Whisper works with usually
SEGMENT_SECONDS = 600


def audio_duration(path: str) -> float:
    # length of an audio file in seconds, read with ffprobe (0.0 if it can't be determined)
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def prepare_audio(path: str, filename: str, out_dir: str, segment_seconds: int = SEGMENT_SECONDS) -> list[str]:
    """
    convert an audio/video file to mono 16 kHz MP3 segments in out_dir; returns their paths in order
    one ffmpeg run does everything: reads any format it knows (mp3, m4a, wav, ogg, webm, mp4 ...),
    drops the video track, converts the sound, and writes segment_000.mp3, segment_001.mp3, ...
    of at most `segment_seconds` each (the "segment" muxer)
    """
    result = subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-i", path,
            "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k",  # drop video; mono, 16 kHz, low bitrate
            # cut into segments; every segment's timestamps start at 0, as if it were its own file
            "-f", "segment", "-segment_time", str(segment_seconds), "-reset_timestamps", "1",
            os.path.join(out_dir, "segment_%03d.mp3"),
        ],
        capture_output=True, text=True,
    )
    #numbered names sort in playback order
    segments = sorted(glob.glob(os.path.join(out_dir, "segment_*.mp3")))
    if result.returncode != 0 or not segments:
        raise ProcessingError(f'"{filename}" could not be read as audio or video (is there a sound track?).')
    return segments
