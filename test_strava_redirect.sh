#!/bin/bash
# Test script to check redirect URI

echo "Testing Strava OAuth redirect URI..."
echo ""
echo "Option 1: Use localhost (current)"
echo "  Callback Domain: localhost"
echo "  Redirect URI: http://localhost:8000/strava/callback"
echo ""
echo "Option 2: Use 127.0.0.1 (try this if localhost doesn't work)"
echo "  Callback Domain: 127.0.0.1"
echo "  Redirect URI: http://127.0.0.1:8000/strava/callback"
echo ""
echo "To test Option 2, update Strava settings and restart server with:"
echo "  export STRAVA_REDIRECT_URI=http://127.0.0.1:8000/strava/callback"
