import html
import os
import re
import sys
import json
from pathlib import Path
from typing import Any

import requests
from tools import ReadGitHubFilesParams, read_github_files, tools
from dotenv import load_dotenv
from openai import OpenAI

from pydantic import ValidationError


load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GITHUB_HEADERS = {
    "User-Agent": "AIP444-Lab-03",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2026-03-10",
}


def print_header() -> None:
    print("=" * 60)
    print("       AIP444 - Lab 3: GitHub PR Reading Partner")
    print("=" * 60)


def is_valid_pr_url(url: str, pr_details: dict[str, str | None]) -> bool:
    """Validate a GitHub PR URL and extract owner, repo, and PR number."""
    if not url.startswith("https://github.com/"):
        print("Error: Must be a Github PR URL")
        return False

    cleaned = url.rstrip("/")
    parts = cleaned[len("https://github.com/") :].split("/")

    if len(parts) != 4 or parts[2] != "pull" or not parts[3].isdigit():
        print("Error: URL must be in format https://github.com/OWNER/REPO/pull/PR_NUMBER")
        return False

    pr_details["owner"] = parts[0]
    pr_details["repo"] = parts[1]
    pr_details["pr_number"] = parts[3]
    return True


def construct_diff_url(base_url: str) -> str:
    """Fetch and, if needed, truncate the PR diff."""
    diff_url = base_url.rstrip("/") + ".diff"
    response = requests.get(diff_url, headers={"User-Agent": "AIP444-Lab-03"})

    if response.status_code != 200:
        raise Exception(f"Failed to fetch diff: HTTP {response.status_code}")

    diff = response.text
    if len(diff) > 95000:
        print(" Diff exceeds 95,000 characters. Truncating context.")
        diff = diff[:95000] + "\n...[Diff Truncated]..."

    return diff


def fetch_pull_request(
    owner: str,
    repo: str,
    issue_num: int,
) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{issue_num}"
    
    response = requests.get(url, headers=GITHUB_HEADERS)

    if response.status_code != 200:
        raise Exception(f"GitHub API Error: {response.status_code}")

    data = response.json()

    return {
        "title": data["title"],
        "body": data["body"] or "[No description provided]",
        "author": data["user"]["login"],
        "created_at": data["created_at"],
        "url": data["html_url"],
        "file_context": {
            "owner": data["head"]["repo"]["owner"]["login"],
            "repo": data["head"]["repo"]["name"],
            "ref": data["head"]["sha"],
        },
    }

def fetch_comments(
    owner: str,
    repo: str,
    issue_num: int,
) -> list[dict[str, str]]:
    url = (
        f"https://api.github.com/repos/{owner}/{repo}/issues/"
        f"{issue_num}/comments?per_page=100"
    )

    response = requests.get(url, headers=GITHUB_HEADERS)

    if response.status_code != 200:
        raise Exception(f"GitHub API Error: {response.status_code}")

    return [
        {
            "username": item["user"]["login"],
            "body": item["body"] or "[No message content]",
            "date": item["created_at"],
        }
        for item in response.json()
    ]

def get_file_contents(path: str | Path, description: str) -> str:
    """Read a file and return the content, or exit on error."""
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: {description} not found at {path}")
        sys.exit(1)
    except Exception as err:  # pragma: no cover - simple CLI UX
        print(f"Error reading {description}: {path}\n   {err}")
        sys.exit(1)


def format_comments(comments: list[dict[str, str]]) -> str:
    """Escape untrusted comment content and format as XML."""
    if not comments:
        return "  [No comments in this thread]"

    xml_parts = []
    for comment in comments:
        safe_author = html.escape(comment["username"])
        safe_date = html.escape(comment["date"])
        safe_body = html.escape(comment["body"])
        xml_parts.append(
            f'  <comment username="{safe_author}" date="{safe_date}">\n{safe_body}\n  </comment>'
        )
    return "\n".join(xml_parts)


def generate_pr_report(
    pr_info: dict[str, Any],
    diff: str,
    comments: list[dict[str, str]],
    user_interpretation: str,
    user_question: str,
) -> str:
    """Construct the prompt and call OpenRouter for the learning report."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY environment variable not set.")

    system_prompt = get_file_contents(
        Path(__file__).resolve().parent / "SYSTEM_PROMPT.md",
        "System prompt file",
    )

    user_prompt = f"""<pull-request>
  <title>{html.escape(pr_info['title'])}</title>
  <author>{html.escape(pr_info['author'])}</author>
  <created-at>{html.escape(pr_info['created_at'])}</created-at>
  <url>{html.escape(pr_info['url'])}</url>
  <file_context>
    <owner>{html.escape(pr_info['file_context']['owner'])}</owner>
    <repo>{html.escape(pr_info['file_context']['repo'])}</repo>
    <ref>{html.escape(pr_info['file_context']['ref'])}</ref>
  </file_context>
  <description>
{html.escape(pr_info['body'])}
  </description>
</pull-request>

```diff
{diff}
```

<thread>
{format_comments(comments)}
</thread>

<student-understanding>
  <interpretation>
{html.escape(user_interpretation)}
  </interpretation>

  <question>
{html.escape(user_question)}
  </question>
</student-understanding>
"""

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    max_iterations = 5
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        response = client.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=messages,
            tools=tools,
        )

        assistant_message = response.choices[0].message

        # Check if there is a tool call to be done; if none, we have the final report
        if not assistant_message.tool_calls:
            return assistant_message.content or ""

        # Maintain conversation history with the assistant's tool call intent
        messages.append(assistant_message)

        # Execute each requested tool call
        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name

            if function_name == "read_github_files":
                try:
                    args = ReadGitHubFilesParams.model_validate_json(
                        tool_call.function.arguments
                    )

                    files = []
                    for file in args.files:
                        item = file.model_dump()
                        # Apply defaults when start_line or max_lines is null
                        item["start_line"] = (
                            1 if file.start_line is None else file.start_line
                        )
                        item["max_lines"] = (
                            500 if file.max_lines is None else file.max_lines
                        )
                        files.append(item)
                        print(
                            f"[Tool Call] read_github_files: path='{item['path']}', "
                            f"lines {item['start_line']} to {item['start_line'] + item['max_lines'] - 1} "
                            f"(ref: {item['ref'][:7]})"
                        )

                    result = read_github_files(files)

                except ValidationError as val_err:
                    print(f"[Tool Error] Invalid arguments passed: {val_err}")
                    result = f"Error: Tool arguments validation failed: {str(val_err)}"

            else:
                print(f"[Tool Error] Unknown tool requested: {function_name}")
                result = f"Error: Unknown tool '{function_name}'"

            # Add tool execution result back to messages
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    return "Max iterations reached without a final report."

def save_report(report: str, owner: str, repo: str, issue_num: int) -> Path:
    """Save the generated Markdown report beside this script."""
    filename = re.sub(r"[^A-Za-z0-9._-]", "-", f"{owner}-{repo}-pr-{issue_num}-report")
    report_path = Path(__file__).resolve().parent / f"{filename}.md"
    try:
        report_path.write_text(report, encoding="utf-8")
    except OSError as err:
        print(f"Error saving Markdown report to {report_path}: {err}")
        sys.exit(1)
    return report_path


def main() -> None:
    print_header()

    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY environment variable not set.")
        sys.exit(1)

    if len(sys.argv) > 1:
        url = sys.argv[1].strip()
    else:
        url = input("Enter GitHub PR URL: ").strip()

    pr_details: dict[str, str | None] = {"owner": None, "repo": None, "pr_number": None}
    if not is_valid_pr_url(url, pr_details):
        sys.exit(1)

    owner = pr_details["owner"]
    repo = pr_details["repo"]
    issue_num = int(pr_details["pr_number"])

    print(f"\nFetching PR #{issue_num} from {owner}/{repo}...")
    try:
        pr_info = fetch_pull_request(owner, repo, issue_num)
        comments = fetch_comments(owner, repo, issue_num)
        diff = construct_diff_url(url)
    except Exception as exc:
        print(f"Error fetching PR data: {exc}")
        sys.exit(1)

    print("PR data and diff loaded successfully.\n")

    print("=" * 60)
    print("In 2-4 sentences, what do you think this PR is changing, and why?")
    user_interpretation = input("> ").strip()

    print("\nWhat is one thing about the PR that you don't understand yet?")
    user_question = input("> ").strip()

    report = generate_pr_report(
        pr_info=pr_info,
        diff=diff,
        comments=comments,
        user_interpretation=user_interpretation,
        user_question=user_question,
    )
    report_path = save_report(report, owner, repo, issue_num)

    print("\n" + "=" * 60)
    print(f"PR LEARNING REPORT — saved to {report_path}")
    print("=" * 60 + "\n")
    print(report)


if __name__ == "__main__":
    main()