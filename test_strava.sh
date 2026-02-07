#!/bin/bash
# Quick script to test Strava OAuth

echo "🏊 Strava OAuth Test Setup"
echo ""
echo "Please provide your Strava API credentials:"
echo "Get them from: https://www.strava.com/settings/api"
echo ""
read -p "Enter STRAVA_CLIENT_ID: " CLIENT_ID
read -p "Enter STRAVA_CLIENT_SECRET: " CLIENT_SECRET
echo ""
echo "Setting environment variables..."
export STRAVA_ENABLED=true
export STRAVA_CLIENT_ID=$CLIENT_ID
export STRAVA_CLIENT_SECRET=$CLIENT_SECRET
export STRAVA_REDIRECT_URI=http://localhost:8000/strava/callback
echo ""
echo "✅ Environment variables set!"
echo ""
echo "Starting server with Strava enabled..."
echo "Open http://localhost:8000 and click 'Connect Strava' tab"
echo ""
cd fastapi_dashboard
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
