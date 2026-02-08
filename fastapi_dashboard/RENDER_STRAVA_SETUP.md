# Strava Setup for Render Deployment

## Required Environment Variables

For Strava integration to work on Render, you need to set these environment variables:

### 1. Enable Strava
```
STRAVA_ENABLED=true
```

### 2. Strava OAuth Credentials
```
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REDIRECT_URI=https://coros-fit-analysis.onrender.com/strava/callback
STRAVA_SCOPE=activity:read_all,profile:read_all
```

### 3. Database (Required for token storage)
```
DATABASE_URL=postgresql://postgres.xxx:[PASSWORD]@aws-1-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
DB_AUTO_CREATE=true
```

## Common Issues

### "Strava access token expired or invalid"

This error means:
1. **Token refresh failed** - Most likely because `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` are not set in Render
2. **Refresh token expired** - User needs to reconnect Strava

### Solution Steps

1. **Verify Strava credentials are set in Render:**
   - Render Dashboard → Your Service → Environment
   - Check that all 4 Strava variables are set:
     - `STRAVA_ENABLED=true`
     - `STRAVA_CLIENT_ID=...`
     - `STRAVA_CLIENT_SECRET=...`
     - `STRAVA_REDIRECT_URI=https://coros-fit-analysis.onrender.com/strava/callback`

2. **Reconnect Strava:**
   - Go to your app: `https://coros-fit-analysis.onrender.com`
   - Click "Connect Strava" tab
   - Click "Connect Strava" button
   - Authorize the app
   - This will store fresh tokens in the database

3. **Check Render logs:**
   - Render Dashboard → Your Service → Logs
   - Look for errors like:
     - "WARNING: Strava client credentials not configured"
     - "ERROR: Strava token refresh failed"
   - These will tell you what's wrong

## Token Refresh Flow

When you click "Load Activities":
1. App checks if token is expired (with 60s buffer)
2. If expired, tries to refresh using `refresh_token`
3. If refresh succeeds, uses new token
4. If refresh fails, shows error asking to reconnect

## Why Reconnection is Needed

If the refresh token itself is expired or invalid, the only solution is to reconnect Strava to get fresh tokens. This happens when:
- User hasn't used the app for a long time
- Tokens were revoked
- Initial token storage had issues

## Quick Fix Checklist

- [ ] `STRAVA_ENABLED=true` is set
- [ ] `STRAVA_CLIENT_ID` is set (your actual client ID)
- [ ] `STRAVA_CLIENT_SECRET` is set (your actual secret)
- [ ] `STRAVA_REDIRECT_URI` matches your Render URL
- [ ] `DATABASE_URL` is set (with pooler connection)
- [ ] User has reconnected Strava after database was set up
