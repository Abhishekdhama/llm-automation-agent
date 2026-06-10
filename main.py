"""
main.py — FastAPI application for the LLM Automation Agent.

Exposes two endpoints:
  - GET  /read   → Read file contents (restricted to /data directory)
  - POST /run    → Execute natural-language tasks via LLM + routing
  - GET  /health → Health check endpoint
"""

import os
import logging
import subprocess

from fastapi import FastAPI, HTTPException, Query  # type: ignore
from pydantic import BaseModel  # type: ignore
from dotenv import load_dotenv  # type: ignore

from functions import (
    DAYS_MAP,
    get_task_output,
    count_days,
    extract_dayname,
    extract_package,
    get_correct_pkgname,
    extract_sort_params,
    sort_csv_data,
    extract_emails_from_file,
    csv_to_json,
    text_to_json,
    count_words,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

AIPROXY_TOKEN: str | None = os.getenv("AIPROXY_TOKEN")
DATA_DIR: str = os.getenv("DATA_DIR", "/data")

if not AIPROXY_TOKEN:
    logger.warning("AIPROXY_TOKEN is not set. LLM features will not work.")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="LLM Automation Agent",
    description="An AI-powered automation agent that accepts natural language tasks.",
    version="2.0.0",
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------
class TaskRequest(BaseModel):
    """Request body for the /run endpoint."""
    task: str


class TaskResponse(BaseModel):
    """Response body for the /run endpoint."""
    status: str
    task_output: str | None = None
    detail: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and Docker HEALTHCHECK."""
    return {"status": "healthy"}


@app.get("/read")
async def read_file(path: str = Query(..., description="File path to read (must be under /data)")):
    """Read the contents of a file.

    Only files under the ``/data`` directory are accessible.
    Uses ``os.path.realpath`` to prevent path traversal attacks.
    """
    # Normalize and resolve the path to prevent traversal
    real_path = os.path.realpath(path)
    allowed_root = os.path.realpath(DATA_DIR)

    if not real_path.startswith(allowed_root):
        raise HTTPException(
            status_code=403,
            detail="Access denied: path must be under the data directory.",
        )

    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail="File not found.")

    if not os.path.isfile(real_path):
        raise HTTPException(status_code=400, detail="Path is not a file.")

    try:
        with open(real_path, "r", encoding="utf-8") as f:
            content = f.read()
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied.")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not a text file.")

    return {"content": content}


@app.post("/run", response_model=TaskResponse)
async def run_task(request: TaskRequest):
    """Execute a natural-language task.

    The task string is sent to the LLM for interpretation, then routed
    to the appropriate handler based on keyword matching:

    - **count <weekday>**: Count occurrences of a weekday in dates.txt
    - **install <package>**: Fuzzy-match and install a PyPI package
    - **sort <file>**: Sort a CSV file by a column
    - **extract emails <file>**: Extract email addresses from a file
    - **convert <file> to json**: Convert CSV/text to JSON
    - **count words <file>**: Count words, lines, and characters
    """
    if not AIPROXY_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: AIPROXY_TOKEN is not set.",
        )

    task = request.task
    task_lower = task.lower()

    try:
        # Get LLM interpretation of the task
        task_output = get_task_output(AIPROXY_TOKEN, task)

        # ---- Task Routing ----

        # 1. Count weekdays in dates
        if "count" in task_lower and any(day in task_lower for day in DAYS_MAP):
            dayname = extract_dayname(task_lower)
            if dayname:
                result = count_days(dayname, data_dir=DATA_DIR)
                return TaskResponse(
                    status="success",
                    task_output=task_output,
                    detail=f"Counted {result} occurrence(s) of '{dayname}'.",
                )

        # 2. Install a PyPI package
        elif "install" in task_lower:
            pkgname = extract_package(task_lower)
            if pkgname:
                correct_package = get_correct_pkgname(pkgname)
                if correct_package:
                    result = subprocess.run(
                        ["pip", "install", correct_package],
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    return TaskResponse(
                        status="success" if result.returncode == 0 else "error",
                        task_output=task_output,
                        detail=f"pip install {correct_package}: {'OK' if result.returncode == 0 else result.stderr[:200]}",
                    )
                else:
                    return TaskResponse(
                        status="error",
                        task_output=task_output,
                        detail=f"No matching package found for '{pkgname}'.",
                    )

        # 3. Sort a CSV file
        elif "sort" in task_lower:
            params = extract_sort_params(task_lower)
            if params["file"]:
                input_path = os.path.join(DATA_DIR, params["file"])
                output_path = os.path.join(DATA_DIR, f"sorted_{params['file']}")
                reverse = "descend" in task_lower
                detail = sort_csv_data(input_path, output_path, params["column"], reverse)
                return TaskResponse(
                    status="success",
                    task_output=task_output,
                    detail=detail,
                )

        # 4. Extract emails from a file
        elif "extract" in task_lower and "email" in task_lower:
            file_match = _extract_filepath(task_lower)
            if file_match:
                input_path = os.path.join(DATA_DIR, file_match)
                output_path = os.path.join(DATA_DIR, "extracted_emails.txt")
                emails = extract_emails_from_file(input_path, output_path)
                return TaskResponse(
                    status="success",
                    task_output=task_output,
                    detail=f"Extracted {len(emails)} email(s) → {output_path}",
                )

        # 5. Convert file to JSON
        elif "convert" in task_lower and "json" in task_lower:
            file_match = _extract_filepath(task_lower)
            if file_match:
                input_path = os.path.join(DATA_DIR, file_match)
                output_path = os.path.join(
                    DATA_DIR,
                    os.path.splitext(file_match)[0] + ".json",
                )
                if file_match.endswith(".csv"):
                    detail = csv_to_json(input_path, output_path)
                else:
                    detail = text_to_json(input_path, output_path)
                return TaskResponse(
                    status="success",
                    task_output=task_output,
                    detail=detail,
                )

        # 6. Count words / characters in a file
        elif "count" in task_lower and ("word" in task_lower or "character" in task_lower):
            file_match = _extract_filepath(task_lower)
            if file_match:
                input_path = os.path.join(DATA_DIR, file_match)
                output_path = os.path.join(DATA_DIR, "word_count.json")
                result = count_words(input_path, output_path)
                return TaskResponse(
                    status="success",
                    task_output=task_output,
                    detail=f"Words: {result['words']}, Lines: {result['lines']}, Chars: {result['characters']}",
                )

        # Fallback: unrecognized task
        return TaskResponse(
            status="not_implemented",
            task_output=task_output,
            detail="Task was interpreted by the LLM but no matching handler was found.",
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Package installation timed out.")
    except Exception as e:
        logger.exception("Unexpected error processing task: %s", task)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_filepath(task: str) -> str:
    """Extract a file path from the task string.

    Looks for common file patterns like 'data.csv', 'notes.txt', etc.

    Args:
        task: The lowercase task string.

    Returns:
        The matched filename or empty string.
    """
    import re
    match = re.search(r"([\w\-]+\.(?:csv|txt|json|md|log))", task)
    return match.group(1) if match else ""
