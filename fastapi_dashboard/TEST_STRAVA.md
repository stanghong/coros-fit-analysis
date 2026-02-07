# Testing Strava OAuth Integration

## Prerequisites

1. **Get Strava API Credentials:**
   - Go to https://www.strava.com/settings/api
   - Click "Create App" or use existing app
   - Note your **Client ID** and **Client Secret**
   - Set **Authorization Callback Domain** to: `localhost` (for local testing)

## Setup for Local Testing

### Option 1: Environment Variables (Recommended)

Export environment variables before starting the server:

```bash
export STRAVA_ENABLED=true
export STRAVA_CLIENT_ID=your_client_id_here
export STRAVA_CLIENT_SECRET=your_client_secret_here
export STRAVA_REDIRECT_URI=http://localhost:8000/strava/callback
```

Then start the server:
```bash
cd fastapi_dashboard
./start.sh
```

### Option 2: Create .env File

Create a `.env` file in `fastapi_dashboard/` directory:

```bash
STRAVA_ENABLED=true
STRAVA_CLIENT_ID=your_client_id_here
STRAVA_CLIENT_SECRET=your_client_secret_here
STRAVA_REDIRECT_URI=http://localhost:8000/strava/callback
```

**Note:** You'll need to modify the startup script to load `.env` file, or use a package like `python-dotenv`.

## Testing Steps

1. **Start the server** with Strava enabled
2. **Open the dashboard** in your browser: http://localhost:8000
3. **Click the "Connect Strava" tab** (should be visible if `STRAVA_ENABLED=true`)
4. **Click "Connect Strava" button** - this redirects to Strava authorization
5. **Authorize the app** on Strava's website
6. **You'll be redirected back** to the dashboard with `?strava_connected=true`
7. **Click "Import Latest Activity"** to fetch activities from Strava

## Expected Behavior

- **Before connection:** Shows "Connect Strava" button
- **After connection:** Shows "Import Latest Activity" button and athlete info
- **After import:** Displays list of activities (currently logged to console)

## Troubleshooting

### "Strava OAuth not configured" error
- Check that all environment variables are set correctly
- Verify `STRAVA_ENABLED=true` is set

### "httpx library not installed" error
- Run: `pip install httpx`

### Redirect URI mismatch
- Make sure the redirect URI in Strava settings matches exactly: `http://localhost:8000/strava/callback`
- For production, update to your production URL

### Connection works but import fails
- Check browser console for errors
- Verify access token is stored (check server logs)
- Token might have expired - reconnect if needed

## Next Steps

After successful connection:
- Activities are fetched but not yet displayed in UI
- Next: Add UI to display activities and allow selection for analysis
- Next: Convert Strava activity data to CSV format for analysis
