#!/bin/bash
# Start server with Strava OAuth enabled for local testing

export STRAVA_ENABLED=true
export STRAVA_CLIENT_ID=200992
export STRAVA_CLIENT_SECRET=b7ee5d76764ba41842774e8b0cbd8fc6e27b92cec
export STRAVA_REDIRECT_URI=http://localhost:8000/strava/callback

echo "🏊 Starting server with Strava OAuth enabled..."
echo ""
echo "Environment variables set:"
echo "  STRAVA_ENABLED=$STRAVA_ENABLED"
echo "  STRAVA_CLIENT_ID=$STRAVA_CLIENT_ID"
echo "  STRAVA_REDIRECT_URI=$STRAVA_REDIRECT_URI"
echo ""
echo "⚠️  Make sure 'Authorization Callback Domain' is set to 'localhost' in Strava settings!"
echo ""
echo "Server starting on http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
