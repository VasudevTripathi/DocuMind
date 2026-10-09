#!/usr/bin/env bash
set -e

# Navigate to backend directory
cd "$(dirname "$0")"

# Create .env only if it does not already exist (never overwrite existing keys)
if [ ! -f .env ]; then
  echo "📄 Creating .env from .env.example..."
  cp .env.example .env
  echo "⚠️ Please edit backend/.env and set your GROQ_API_KEY or GEMINI_API_KEY."
fi

# Activate virtual environment if present
if [ -d ".venv" ]; then
  source .venv/bin/activate
elif [ -d "venv" ]; then
  source venv/bin/activate
fi

# Start FastAPI server
echo "🚀 Starting DocuMind backend on http://localhost:8000..."
exec uvicorn app.main:app --reload --port 8000
