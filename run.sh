#!/usr/bin/env bash
# Run the web2ebook Streamlit app.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Install / upgrade dependencies quietly.
# Tip: activate a virtual environment first to keep your system Python clean:
#   python3 -m venv .venv && source .venv/bin/activate
pip install -q -r requirements.txt

streamlit run app.py "$@"
