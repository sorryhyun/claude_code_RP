#!/bin/bash
# Parse interview transcripts from CSV into evaluation pairs
# Usage: ./parse_transcripts.sh --dataset creatives [--sample 50]

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Forward all arguments to Python script
cd "$PROJECT_ROOT"
uv run python scripts/evaluation/parse_transcripts.py "$@"
