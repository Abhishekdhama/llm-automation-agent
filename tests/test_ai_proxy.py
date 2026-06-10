"""
tests/test_ai_proxy.py — Tests for the AI Proxy integration.

Validates that the AI Proxy API can be called successfully and returns
expected responses. Refactored from the original AI_Proxy.py standalone
script into proper pytest tests.

Usage:
    pytest tests/test_ai_proxy.py -v
    pytest tests/test_ai_proxy.py -v -k test_add_numbers

Note:
    These tests require a valid AIPROXY_TOKEN environment variable.
    Set it in your .env file or export it before running tests.
"""

import os
import pytest
import requests
from dotenv import load_dotenv

# Load .env for the token
load_dotenv()

AI_PROXY_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")


def _call_ai_proxy(messages: list[dict], temperature: float = 0, max_tokens: int = 50) -> str:
    """Helper to call the AI Proxy API.

    Args:
        messages: List of message dicts for the chat API.
        temperature: Sampling temperature (0 = deterministic).
        max_tokens: Maximum tokens in the response.

    Returns:
        The response text content.

    Raises:
        requests.HTTPError: If the API returns an error status.
        ValueError: If the token is not set.
    """
    if not AIPROXY_TOKEN:
        raise ValueError(
            "AIPROXY_TOKEN is not set. "
            "Set it in your .env file or as an environment variable."
        )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AIPROXY_TOKEN}",
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(AI_PROXY_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not AIPROXY_TOKEN,
    reason="AIPROXY_TOKEN not set — skipping live API tests.",
)
class TestAIProxy:
    """Tests for AI Proxy API integration."""

    def test_add_two_numbers(self):
        """Test that the LLM can add two numbers correctly."""
        num1, num2 = 5, 3
        messages = [
            {
                "role": "system",
                "content": "You are a Python calculator. Respond with ONLY the numeric result, nothing else.",
            },
            {
                "role": "user",
                "content": f"Add {num1} and {num2}",
            },
        ]

        result = _call_ai_proxy(messages)
        # The LLM should return "8" or a string containing 8
        assert "8" in result, f"Expected '8' in response, got: '{result}'"

    def test_simple_greeting(self):
        """Test that the LLM responds to a basic greeting."""
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Keep responses under 20 words.",
            },
            {
                "role": "user",
                "content": "Say hello",
            },
        ]

        result = _call_ai_proxy(messages)
        assert len(result) > 0, "Expected a non-empty response"

    def test_api_returns_valid_json(self):
        """Test that the API returns properly formatted JSON."""
        if not AIPROXY_TOKEN:
            pytest.skip("No token")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AIPROXY_TOKEN}",
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 10,
        }

        response = requests.post(AI_PROXY_URL, headers=headers, json=payload, timeout=30)
        assert response.status_code == 200

        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "message" in data["choices"][0]


# ---------------------------------------------------------------------------
# Standalone runner (for quick manual testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not AIPROXY_TOKEN:
        print("ERROR: AIPROXY_TOKEN not set. Add it to your .env file.")
    else:
        print("Testing AI Proxy connection...")
        try:
            result = _call_ai_proxy(
                messages=[
                    {"role": "system", "content": "You are a calculator. Reply with only the number."},
                    {"role": "user", "content": "What is 5 + 3?"},
                ]
            )
            print(f"✓ AI Proxy responded: {result}")
        except Exception as e:
            print(f"✗ Error: {e}")
