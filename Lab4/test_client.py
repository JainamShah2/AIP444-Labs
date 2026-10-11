import json
import time
from pathlib import Path

import requests

notes_path = Path(__file__).resolve().parent / "notes.md"


def test_server() -> None:
    try:
        print(f"Reading notes from: {notes_path}")
        notes_content = notes_path.read_text(encoding="utf-8")

        payload = {
            "notes": notes_content,
            "cards": 2,
        }

        print("Sending request to server...")
        start_time = time.time()

        response = requests.post(
            "http://localhost:3000/api/generate",
            json=payload,
            timeout=120,
        )

        elapsed = time.time() - start_time
        print(f"Request took {elapsed:.2f}s")

        if response.status_code != 200:
            print(f"Server error {response.status_code}: {response.text}")
            return

        data = response.json()
        print("\nSuccess! Received Structured Data:")
        print(json.dumps(data, indent=2))

    except FileNotFoundError:
        print(f"Error: Could not find file at {notes_path}")
    except Exception as exc:
        print(f"Error: {exc}")


if __name__ == "__main__":
    test_server()