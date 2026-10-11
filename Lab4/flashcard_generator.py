import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from openai import OpenAI

from schemas import FlashcardResponse

load_dotenv(find_dotenv())
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def get_file_contents(path: str | Path, description: str) -> str:
    """Read a file and raise a clear error if it cannot be accessed."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as error:
        raise RuntimeError(f"Unable to read {description} at {path}: {error}") from error


async def generate_flashcards(notes: str, cards: int) -> FlashcardResponse:
    """Generate structured flashcards from the provided notes."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY environment variable is not set.")

    prompt_path = Path(__file__).resolve().parent / "SYSTEM_PROMPT.md"
    system_prompt = get_file_contents(prompt_path, "System prompt file")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    completion = client.chat.completions.parse(
        model="google/gemini-2.5-flash",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Here are the notes:\n<notes>\n{notes}\n</notes>\n\n"
                    f"Please create exactly {cards} flashcards based on these notes."
                ),
            },
        ],
        response_format=FlashcardResponse,
    )

    message = completion.choices[0].message
    if message.parsed is None:
        if message.refusal:
            raise RuntimeError(f"The model refused to generate flashcards: {message.refusal}")
        raise RuntimeError("The model response did not contain parsed flashcards.")

    return message.parsed
