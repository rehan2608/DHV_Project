#!/usr/bin/env bash
# ==============================================================================
# NIRF Analytics & Visualization Engine - Web Application Runner
# ==============================================================================
# Usage:
#   ./run.sh
#   or
#   bash run.sh
# ==============================================================================

set -e

# Change directory to project root
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=================================================================="
echo "  🎓 NIRF Analytics & Visualization Platform"
echo "=================================================================="
echo "📂 Project root: $PROJECT_DIR"

# 1. Activate Virtual Environment (if exists)
if [ -d "$PROJECT_DIR/.venv" ]; then
    echo "⚡ Activating virtual environment (.venv)..."
    source "$PROJECT_DIR/.venv/bin/activate"
elif [ -d "$PROJECT_DIR/venv" ]; then
    echo "⚡ Activating virtual environment (venv)..."
    source "$PROJECT_DIR/venv/bin/activate"
elif command -v conda &> /dev/null && [ -n "$CONDA_DEFAULT_ENV" ]; then
    echo "⚡ Using active Conda environment: $CONDA_DEFAULT_ENV"
fi

# 2. Check for Streamlit
if ! command -v streamlit &> /dev/null; then
    echo "❌ Error: 'streamlit' command not found."
    echo "Please install requirements first using: pip install -r requirements.txt"
    exit 1
fi

PORT=${PORT:-8501}

echo "🚀 Starting Streamlit application on http://localhost:$PORT..."
echo "💡 Press Ctrl+C to stop the server."
echo "=================================================================="

# 3. Launch Streamlit app
exec streamlit run scripts/nirf_query_playground.py \
    --server.port "$PORT" \
    --server.headless false \
    --browser.gatherUsageStats false

