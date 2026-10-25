"""Speech to text. Only the mock exists until the provider is chosen (Phase 7)."""
import os

from app import config

MOCK_TRANSCRIPT = (
    "This is a placeholder transcript, because transcription runs in mock mode. "
    "In a real lecture the speaker would introduce the topic of the day and explain why it matters. "
    "Then the main ideas would follow, one after another, with examples that make them concrete. "
    "A good lecture connects every new idea to something the students already know. "
    "Definitions are given first, and then they are applied to small problems. "
    "The lecturer might pause to ask the audience a question and wait for answers. "
    "Mistakes that students often make are pointed out, together with ways to avoid them. "
    "Towards the end, the most important points are repeated as a short summary. "
    "Finally, the lecturer suggests what to read before the next session and which exercises to try. "
    "Students are encouraged to review their notes within a day, because memory fades quickly without practice. "
    "Spaced repetition and self-testing are mentioned as the most effective ways to study. "
    "The session closes with time for questions from the audience."
)


def transcribe(audio_path: str) -> str:
    if config.TRANSCRIBE_PROVIDER == "mock":
        return f"(Mock transcript of {os.path.basename(audio_path)}.) {MOCK_TRANSCRIPT}"
    raise RuntimeError(f"TRANSCRIBE_PROVIDER={config.TRANSCRIBE_PROVIDER} is not implemented yet.")
