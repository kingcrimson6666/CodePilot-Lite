"""Check required environment variables for the assistant."""

import os
import sys

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

REQUIRED = ["LLM_MODEL_ID", "LLM_API_KEY", "LLM_BASE_URL"]


def main() -> int:
    if load_dotenv:
        load_dotenv()
    missing = [key for key in REQUIRED if not os.getenv(key)]
    if missing:
        print("Missing required env vars: " + ", ".join(missing))
        return 1
    print("Environment looks good.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
