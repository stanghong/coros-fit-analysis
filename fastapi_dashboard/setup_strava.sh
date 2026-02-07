#!/bin/bash
# Setup script for Strava OAuth testing

echo "🏊 Strava OAuth Setup"
echo ""
echo "Your Client ID: 200992"
echo ""
echo "Please provide your Client Secret (click 'Show' in Strava to reveal it):"
read -sp "Enter STRAVA_CLIENT_SECRET: " CLIENT_SECRET
echo ""
echo ""
echo "Setting environment variables..."
export STRAVA_ENABLED=true
export STRAVA_CLIENT_ID=200992
export STRAVA_CLIENT_SECRET=$CLIENT_SECRET
export STRAVA_REDIRECT_URI=http://localhost:8000/strava/callback

echo "✅ Environment variables set!"
echo ""
echo "⚠️  IMPORTANT: Make sure you've set 'Authorization Callback Domain' to 'localhost' in Strava settings!"
echo ""
echo "Starting server with Strava enabled..."
echo "Open http://localhost:8000 and click 'Connect Strava' tab"
echo ""
cd "$(dirname "$0")"
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
