"""
functions.py — Core task functions for the LLM Automation Agent.

Provides utilities for:
- LLM interaction via AI Proxy (GPT-4o-mini)
- Date/weekday counting in data files
- PyPI package name fuzzy matching (with caching)
- CSV sorting
- Email extraction from text
- JSON format conversion
- Word/character counting
"""

import os
import re
import csv
import json
import logging
from io import StringIO
from datetime import datetime
from typing import Optional

from openai import OpenAI  # type: ignore
from thefuzz import fuzz

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DAYS_MAP: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

AI_PROXY_BASE_URL = "https://aiproxy.sanand.workers.dev/openai/v1"

# In-memory cache for the package list (loaded once, reused)
_packages_cache: list[str] | None = None

# ---------------------------------------------------------------------------
# LLM Interaction
# ---------------------------------------------------------------------------

def get_task_output(aiproxy_token: str, task: str) -> str:
    """Send a task to GPT-4o-mini via AI Proxy and return the response.

    Args:
        aiproxy_token: The AI Proxy authentication token.
        task: The natural language task to send to the LLM.

    Returns:
        The LLM's response text, stripped of whitespace.

    Raises:
        ValueError: If the token is missing or empty.
        openai.APIError: If the API call fails.
    """
    if not aiproxy_token:
        raise ValueError("AIPROXY_TOKEN is not set. Check your .env file.")

    client = OpenAI(
        api_key=aiproxy_token,
        base_url=AI_PROXY_BASE_URL,
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": task}],
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Task: Count Weekdays
# ---------------------------------------------------------------------------

def count_days(dayname: str, data_dir: str = "/data") -> int:
    """Count how many dates in dates.txt fall on a given weekday.

    Reads ``{data_dir}/dates.txt``, counts lines whose date matches the
    requested weekday, and writes the count to ``{data_dir}/{day}-count``.

    Args:
        dayname: A weekday name (e.g., "monday", "sundays", "Wednesday").
        data_dir: Path to the data directory. Defaults to ``/data``.

    Returns:
        The count of matching dates.

    Raises:
        FileNotFoundError: If dates.txt does not exist.
        ValueError: If dayname does not match any known weekday.
    """
    dayvalue: int = -1
    day_key: Optional[str] = None

    for day, value in DAYS_MAP.items():
        if day in dayname.lower():
            dayvalue = value
            day_key = day
            break

    if dayvalue == -1 or day_key is None:
        raise ValueError(f"Unknown weekday in: '{dayname}'")

    dates_path = os.path.join(data_dir, "dates.txt")
    with open(dates_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    count = sum(
        1
        for line in lines
        if line.strip()
        and datetime.strptime(line.strip(), "%Y-%m-%d").weekday() == dayvalue
    )

    output_path = os.path.join(data_dir, f"{day_key}-count")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(str(count))

    logger.info("Counted %d %ss in %s", count, day_key, dates_path)
    return count


def extract_dayname(task: str) -> str:
    """Extract the weekday name following 'count' in a task string.

    Args:
        task: The natural language task string.

    Returns:
        The extracted word, or an empty string if no match.
    """
    match = re.search(r"count\s+(\w+)", task, re.IGNORECASE)
    return match.group(1) if match else ""


# ---------------------------------------------------------------------------
# Task: Install Package (fuzzy match)
# ---------------------------------------------------------------------------

def extract_package(task: str) -> str:
    """Extract the package name following 'install' in a task string.

    Args:
        task: The natural language task string.

    Returns:
        The extracted package name, or an empty string if no match.
    """
    match = re.search(r"install\s+([\w\-]+)", task, re.IGNORECASE)
    return match.group(1) if match else ""


def _load_packages_cache(cache_file: str = "packages_cache.txt") -> list[str]:
    """Load the cached package list from disk (one package per line).

    The cache is loaded once into memory and reused for subsequent calls.

    Args:
        cache_file: Path to the cached package list file.

    Returns:
        A list of package name strings.

    Raises:
        FileNotFoundError: If the cache file doesn't exist.
            Run ``getpackages.py`` first to generate it.
    """
    global _packages_cache
    if _packages_cache is not None:
        return _packages_cache

    if not os.path.exists(cache_file):
        raise FileNotFoundError(
            f"Package cache '{cache_file}' not found. "
            "Run 'python getpackages.py' to generate it."
        )

    with open(cache_file, "r", encoding="utf-8") as f:
        _packages_cache = [line.strip() for line in f if line.strip()]

    logger.info("Loaded %d packages from cache", len(_packages_cache))
    return _packages_cache


def get_correct_pkgname(
    pkgname: str,
    threshold: int = 90,
    cache_file: str = "packages_cache.txt",
) -> str:
    """Find the closest matching PyPI package name using fuzzy matching.

    Args:
        pkgname: The (possibly misspelled) package name from the user.
        threshold: Minimum fuzz ratio (0-100) for a match. Default 90.
        cache_file: Path to the cached package list.

    Returns:
        The best matching package name, or an empty string if no match.
    """
    packages = _load_packages_cache(cache_file)

    best_match = ""
    best_score = 0

    for pkg in packages:
        score = fuzz.ratio(pkgname.lower(), pkg.lower())
        if score >= threshold and score > best_score:
            best_score = score
            best_match = pkg

    if best_match:
        logger.info(
            "Fuzzy matched '%s' → '%s' (score: %d)", pkgname, best_match, best_score
        )

    return best_match


# ---------------------------------------------------------------------------
# Task: Sort CSV Data
# ---------------------------------------------------------------------------

def sort_csv_data(
    input_path: str,
    output_path: str,
    sort_column: int = 0,
    reverse: bool = False,
) -> str:
    """Sort a CSV file by a specified column.

    Args:
        input_path: Path to the input CSV file.
        output_path: Path to write the sorted CSV.
        sort_column: Zero-based column index to sort by. Default 0.
        reverse: If True, sort in descending order.

    Returns:
        A summary message with the number of rows sorted.

    Raises:
        FileNotFoundError: If the input file doesn't exist.
        IndexError: If sort_column is out of range.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        rows = list(reader)

    if not rows:
        return "CSV file is empty (no data rows)."

    if sort_column >= len(rows[0]):
        raise IndexError(
            f"Column index {sort_column} out of range "
            f"(file has {len(rows[0])} columns)."
        )

    # Try numeric sort, fall back to string sort
    try:
        rows.sort(key=lambda r: float(r[sort_column]), reverse=reverse)
    except (ValueError, IndexError):
        rows.sort(key=lambda r: r[sort_column], reverse=reverse)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if header:
            writer.writerow(header)
        writer.writerows(rows)

    return f"Sorted {len(rows)} rows by column {sort_column} → {output_path}"


def extract_sort_params(task: str) -> dict:
    """Extract sort parameters from a natural language task.

    Looks for patterns like 'sort <file> by column <N>'.

    Args:
        task: The task string.

    Returns:
        Dict with 'file' and 'column' keys.
    """
    file_match = re.search(r"sort\s+([\w/\.\-]+)", task, re.IGNORECASE)
    col_match = re.search(r"column\s+(\d+)", task, re.IGNORECASE)
    return {
        "file": file_match.group(1) if file_match else "",
        "column": int(col_match.group(1)) if col_match else 0,
    }


# ---------------------------------------------------------------------------
# Task: Extract Emails
# ---------------------------------------------------------------------------

def extract_emails(text: str) -> list[str]:
    """Extract all email addresses from a text string.

    Args:
        text: The input text to scan for emails.

    Returns:
        A list of unique email addresses found.
    """
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    emails = re.findall(pattern, text)
    return list(dict.fromkeys(emails))  # preserve order, deduplicate


def extract_emails_from_file(
    input_path: str, output_path: str
) -> list[str]:
    """Extract emails from a file and write them to an output file.

    Args:
        input_path: Path to the input text file.
        output_path: Path to write the extracted emails.

    Returns:
        List of extracted email addresses.

    Raises:
        FileNotFoundError: If the input file doesn't exist.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    emails = extract_emails(content)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(emails))

    logger.info("Extracted %d emails from %s", len(emails), input_path)
    return emails


# ---------------------------------------------------------------------------
# Task: JSON Conversion
# ---------------------------------------------------------------------------

def csv_to_json(input_path: str, output_path: str) -> str:
    """Convert a CSV file to JSON format.

    Args:
        input_path: Path to the CSV file.
        output_path: Path to write the JSON output.

    Returns:
        Summary message with row count.

    Raises:
        FileNotFoundError: If the input file doesn't exist.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    return f"Converted {len(rows)} rows from CSV to JSON → {output_path}"


def text_to_json(input_path: str, output_path: str) -> str:
    """Convert a plain text file (one item per line) to a JSON array.

    Args:
        input_path: Path to the text file.
        output_path: Path to write the JSON output.

    Returns:
        Summary message with item count.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        items = [line.strip() for line in f if line.strip()]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    return f"Converted {len(items)} lines to JSON array → {output_path}"


# ---------------------------------------------------------------------------
# Task: Word / Character Count
# ---------------------------------------------------------------------------

def count_words(input_path: str, output_path: str) -> dict:
    """Count words, lines, and characters in a text file.

    Args:
        input_path: Path to the text file.
        output_path: Path to write the count results.

    Returns:
        Dict with 'words', 'lines', 'characters' keys.

    Raises:
        FileNotFoundError: If the input file doesn't exist.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    result = {
        "words": len(content.split()),
        "lines": content.count("\n") + (1 if content and not content.endswith("\n") else 0),
        "characters": len(content),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    logger.info("Word count for %s: %s", input_path, result)
    return result
