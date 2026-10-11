# FastAPI server that accepts notes through a POST request,
# validates the request data, generates flashcards, and
# returns the results as a JSON response.

"""
This FastAPI application exposes a flashcard-generation endpoint at
POST /api/generate. FastAPI validates the incoming JSON body against the
GenerateRequest Pydantic model, then the route passes the notes and requested
card count to the structured-output generator and returns its Pydantic
response as JSON. CORS middleware permits browser clients, and HTTP
middleware adds request-processing time to each response.
"""

import time

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from flashcard_generator import generate_flashcards

app = FastAPI()

# CORS lets browser-based clients call the API from a different origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add the request duration to the response for client-side diagnostics."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


class GenerateRequest(BaseModel):
    """Expected JSON request body; `cards` defaults to three when omitted."""

    notes: str
    cards: int = 3


@app.post("/api/generate")
async def generate_cards(request: GenerateRequest):
    """Validate a generation request and return the structured flashcards."""
    try:
        result = await generate_flashcards(request.notes, request.cards)
        return result
    except Exception as error:
        print(f"Server Error: {error}")
        raise HTTPException(status_code=500, detail=str(error)) from error

if __name__ == "__main__":
    print("🚀 Server running on http://localhost:3000")
    # Uvicorn runs the FastAPI app and listens on port 3000.
    uvicorn.run(app, host="0.0.0.0", port=3000)