import html
import os
import requests
from typing import Any

GITHUB_HEADERS = {
    "User-Agent": "AIP444-Lab-05",
}

from openai import pydantic_function_tool
from pydantic import BaseModel, ConfigDict, Field


class GitHubFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner: str = Field(
        description=(
            "Repository owner/org. "
            "Use owner from the supplied PR file_context."
        )
    )
    repo: str = Field(
        description=(
            "Repository name. "
            "Use repo from the supplied PR file_context."
        )
    )
    path: str = Field(
        description="File path within the repository, e.g., src/parser.ts."
    )
    ref: str = Field(
        description=(
            "Revision to read. "
            "Use the commit SHA from the supplied PR file_context."
        )
    )
    start_line: int | None = Field(
        ...,
        strict=True,
        ge=1,
        description=(
            "First line to return, using 1-based inclusive numbering. "
            "Use null to start at line 1."
        ),
    )
    max_lines: int | None = Field(
        ...,
        strict=True,
        ge=1,
        le=5000,
        description=(
            "Maximum number of lines to return starting at start_line. "
            "For example, start_line=1800 and max_lines=100 requests "
            "lines 1800–1899. Use null for 500 lines. "
            "Valid non-null values are 1–5,000."
        ),
    )


class ReadGitHubFilesParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files: list[GitHubFile] = Field(
        min_length=1,
        description=(
            "Files to read. Each file has its own revision and line range."
        ),
    )


tools = [
    pydantic_function_tool(
        ReadGitHubFilesParams,
        name="read_github_files",
        description=(
            "Read relevant sections of one or more GitHub files. "
            "Use when the supplied diff and discussion omit code needed "
            "to investigate the student's question or check their interpretation. "
            "Prefer focused line ranges and request more context if needed."
        ),
    )
]

def read_github_files(params: dict[str, Any] | list[dict[str, Any]]) -> str:
    # Handle either a wrapper dict {"files": [...]} or a bare list [...]
    if isinstance(params, dict):
        files = params.get("files")
    elif isinstance(params, list):
        files = params
    else:
        return "Error: Invalid parameter. Expected an object containing a 'files' array."

    if not isinstance(files, list) or not files:
        return "Error: 'files' parameter must be a non-empty list."

    results: list[str] = []

    for idx, file_spec in enumerate(files):
        # 1. Parameter extraction and validation
        owner = file_spec.get("owner")
        repo = file_spec.get("repo")
        path = file_spec.get("path")
        ref = file_spec.get("ref")

        if not all([owner, repo, path, ref]):
            results.append(
                f'<file-error index="{idx}" message="Missing required parameters (owner, repo, path, and ref are required)." />'
            )
            continue

        # Clean leading slashes from file path
        cleaned_path = str(path).lstrip("/")

        # Defaults and bounds checking
        start_line = file_spec.get("start_line")
        if start_line is None or not isinstance(start_line, int) or start_line < 1:
            start_line = 1

        max_lines = file_spec.get("max_lines")
        if max_lines is None or not isinstance(max_lines, int) or max_lines < 1:
            max_lines = 500
        elif max_lines > 5000:
            max_lines = 5000

        # 2. Fetch raw file content
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{cleaned_path}"

        try:
            response = requests.get(raw_url, headers=GITHUB_HEADERS, timeout=15)
            if response.status_code == 404:
                results.append(
                    f'<file-error repo="{owner}/{repo}" path="{cleaned_path}" ref="{ref}" '
                    f'message="File not found (HTTP 404)." />'
                )
                continue
            elif response.status_code == 403:
                results.append(
                    f'<file-error repo="{owner}/{repo}" path="{cleaned_path}" ref="{ref}" '
                    f'message="Access forbidden or rate limit exceeded (HTTP 403)." />'
                )
                continue
            elif response.status_code != 200:
                results.append(
                    f'<file-error repo="{owner}/{repo}" path="{cleaned_path}" ref="{ref}" '
                    f'message="Failed to fetch file: HTTP {response.status_code}." />'
                )
                continue

            content = response.text
        except requests.exceptions.RequestException as err:
            results.append(
                f'<file-error repo="{owner}/{repo}" path="{cleaned_path}" ref="{ref}" '
                f'message="Network request failed: {html.escape(str(err))}" />'
            )
            continue

        # 3. Handle line slicing and numbering
        all_lines = content.splitlines()
        total_lines = len(all_lines)

        start_idx = start_line - 1
        end_idx = start_idx + max_lines
        selected_lines = all_lines[start_idx:end_idx]

        if not selected_lines:
            actual_range = "0-0"
            numbered_body = "  [No lines found in the requested range]"
        else:
            actual_start = start_line
            actual_end = start_line + len(selected_lines) - 1
            actual_range = f"{actual_start}-{actual_end}"

            numbered_body = "\n".join(
                f"{actual_start + i}: {line}"
                for i, line in enumerate(selected_lines)
            )

        # 4. XML Formatting
        xml_output = (
            f'<file repo="{owner}/{repo}" ref="{ref}" path="{cleaned_path}" '
            f'lines="{actual_range}" total-lines="{total_lines}">\n'
            f'{numbered_body}\n'
            f'</file>'
        )
        results.append(xml_output)

    return "\n\n".join(results)