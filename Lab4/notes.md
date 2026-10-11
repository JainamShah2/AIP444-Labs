# FastAPI and Structured Outputs Notes

## Request validation
A FastAPI application can validate incoming JavaScript Object Notation (JSON) using Pydantic models. Each field in the model has a type and optional default values. For example, the request body can require a `notes` string and an integer `cards` value that defaults to 3.

## Why validation matters
Validation ensures that the server rejects malformed input before the business logic runs. This prevents runtime errors and makes the API easier to reason about.

## Structured outputs
The model should return data in a known schema instead of freeform text. This is useful when the application expects a specific JSON shape, such as a list of flashcards.

## JSON response contract
The Application Programming Interface (API) should return a JSON object with a top-level `flashcards` list. Each flashcard should include an application, challenge, answer, evidence, misconception, and correction.

## Example
A backend endpoint can accept notes and generate flashcards from them. The notes are sent as a JSON payload, the server validates the request, and then it calls the model to produce structured flashcards.
