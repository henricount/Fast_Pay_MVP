#!/bin/bash

# Fast Pay MVP Startup Script

echo "🏦 Starting Fast Pay MVP..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Initialize database
echo "🗄️ Initializing database..."
python -c "from app.models.database import init_db; init_db()"

# Start the application
echo "🚀 Starting Fast Pay MVP on http://localhost:8000"
echo "📊 Demo interface: http://localhost:8000"
echo "📖 API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn main:app --host 0.0.0.0 --port 8000 --reload