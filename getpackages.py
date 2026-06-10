"""
getpackages.py — Fetch and cache all PyPI package names.

Scrapes https://pypi.org/simple/ for the complete list of package names
and writes them to a cache file (one package per line) for efficient
fuzzy matching by the automation agent.

Usage:
    python getpackages.py                     # Default: packages_cache.txt
    python getpackages.py my_cache.txt        # Custom output file
"""

import sys
import logging

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PYPI_SIMPLE_URL = "https://pypi.org/simple/"


def fetch_packages(url: str = PYPI_SIMPLE_URL) -> list[str]:
    """Fetch all package names from PyPI Simple API.

    Args:
        url: The PyPI simple index URL.

    Returns:
        A list of package name strings.

    Raises:
        requests.HTTPError: If the HTTP request fails.
    """
    logger.info("Fetching package list from %s ...", url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    packages = [a.text.strip() for a in soup.find_all("a") if a.text.strip()]

    logger.info("Found %d packages.", len(packages))
    return packages


def write_cache(packages: list[str], output_file: str = "packages_cache.txt") -> None:
    """Write package names to a cache file (one per line).

    Using one package per line instead of space-separated makes the file
    much easier to parse and keeps individual line sizes small.

    Args:
        packages: List of package names.
        output_file: Path to the output cache file.
    """
    with open(output_file, "w", encoding="utf-8") as f:
        for pkg in packages:
            f.write(pkg + "\n")

    size_mb = round(len("\n".join(packages)) / (1024 * 1024), 2)
    logger.info("Wrote %d packages to '%s' (~%s MB).", len(packages), output_file, size_mb)


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "packages_cache.txt"

    try:
        pkgs = fetch_packages()
        write_cache(pkgs, output)
        logger.info("Done! Cache file: %s", output)
    except requests.RequestException as e:
        logger.error("Failed to fetch packages: %s", e)
        sys.exit(1)
