#!/bin/bash
echo "🚀 Starting Fast Pay MVP on Railway..."
echo "PORT: $PORT"
echo "Environment: Railway"

# Start the application
python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-keep-alive 30