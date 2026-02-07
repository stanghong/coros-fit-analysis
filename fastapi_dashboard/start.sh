#!/bin/bash
# Start script for Swimming Dashboard

cd "$(dirname "$0")"

echo "🏊 Starting Swimming Workout Dashboard..."
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies if needed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the server
echo "Starting FastAPI server on http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

cd backend
python3 main.py
