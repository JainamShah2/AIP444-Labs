
from typing import List

from pydantic import BaseModel, Field


class Flashcard(BaseModel):
    """A single learning-targeted flashcard based on the provided notes."""

    application: str = Field(
        ...,
        description="A 1-2 sentence real-world scenario where this concept is used or required.",
    )
    challenge: str = Field(
        ...,
        description="A specific problem to solve in the application scenario.",
    )
    answer: str = Field(
        ...,
        description="The correct solution to the challenge, with a brief explanation and all acronyms expanded.",
    )
    evidence: str = Field(
        ...,
        description="A direct quote from the source notes supporting the answer.",
    )
    misconception: str = Field(
        ...,
        description="A misconception a student might say, written as a quote.",
    )
    correction: str = Field(
        ...,
        description="Why the misconception is wrong, using facts from the notes.",
    )


class FlashcardResponse(BaseModel):
    """The top-level JSON object returned by the API."""

    flashcards: List[Flashcard] = Field(
        ...,
        description="List of flashcard objects generated from the provided notes.",
    )

