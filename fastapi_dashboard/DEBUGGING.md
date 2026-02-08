# Debugging Guide

## How to Check Error Logs on Render

### Method 1: Render Dashboard (Recommended)

1. **Go to Render Dashboard**
   - Visit: https://dashboard.render.com
   - Log in to your account

2. **Navigate to Your Service**
   - Click on your service: `coros-fit-analysis` (or whatever you named it)
   - You'll see the service overview page

3. **View Logs**
   - Click on the **"Logs"** tab at the top of the page
   - You'll see real-time logs from your application
   - Scroll down to see recent log entries

4. **Filter Logs**
   - Look for lines containing:
     - `ERROR:` - Error messages
     - `WARNING:` - Warning messages
     - `DEBUG:` - Debug information (if enabled)
     - `INFO:` - Informational messages

5. **Search for Strava-Related Errors**
   - Use Ctrl+F (or Cmd+F on Mac) to search for:
     - `Strava token refresh failed`
     - `ERROR:`
     - `athlete_id`
     - `token`

### Method 2: Render CLI (Advanced)

If you have Render CLI installed:

```bash
# Install Render CLI (if not installed)
npm install -g render-cli

# Login
render login

# View logs
render logs <service-name>
```

### Method 3: Check Specific Endpoints

You can also test endpoints directly to see errors:

1. **Check Token Status**
   ```
   https://coros-fit-analysis.onrender.com/strava/token-check?athlete_id=YOUR_ATHLETE_ID
   ```
   Replace `YOUR_ATHLETE_ID` with your actual Strava athlete ID (you can get this from `/strava/status`)

2. **Check Connection Status**
   ```
   https://coros-fit-analysis.onrender.com/strava/status
   ```

3. **Check API Config**
   ```
   https://coros-fit-analysis.onrender.com/api/config
   ```

## What to Look For in Logs

When you click "Load Activities" and get a 401 error, look for these log entries:

### Expected Log Sequence:

1. **Token Check:**
   ```
   DEBUG: Token exists but refresh failed or token invalid
   DEBUG: Token expires_at: 1234567890, current_time: 1234567891
   DEBUG: Token expired: True
   DEBUG: Has refresh_token: True
   ```

2. **Token Refresh Attempt:**
   ```
   ERROR: Strava token refresh failed (status 400): {...}
   DEBUG: Client ID: 200992... (first 10 chars)
   DEBUG: Has refresh_token: True
   DEBUG: Refresh token length: 40
   ```

3. **Error Response:**
   ```
   ERROR: HTTP error during token refresh: {...}
   ```

## Common Issues and Solutions

### Issue 1: Token Refresh Fails with 400 Bad Request

**Symptoms:**
- Log shows: `ERROR: Strava token refresh failed (status 400)`
- Error detail mentions "invalid refresh_token"

**Possible Causes:**
- Refresh token was revoked
- Refresh token expired (Strava refresh tokens can expire)
- Client credentials are wrong

**Solution:**
- Click "Reconnect Strava" to get a fresh token
- Verify `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` in Render environment variables

### Issue 2: Token Not Found in Database

**Symptoms:**
- Log shows: `No token found for this athlete_id`
- `/strava/status` returns `"connected": false`

**Possible Causes:**
- Token wasn't saved during OAuth callback
- Database connection issue during token save

**Solution:**
- Check database connection: `/api/db-test`
- Check database status: `/api/db-status`
- Reconnect Strava to save token again

### Issue 3: Client Credentials Not Configured

**Symptoms:**
- Log shows: `WARNING: Strava client credentials not configured`
- Token refresh returns `None`

**Solution:**
- Verify these environment variables in Render:
  - `STRAVA_CLIENT_ID`
  - `STRAVA_CLIENT_SECRET`
  - Both must be set and correct

## Quick Debug Checklist

1. ✅ Check Render logs for `ERROR:` messages
2. ✅ Verify environment variables are set correctly
3. ✅ Test `/strava/status` endpoint
4. ✅ Test `/strava/token-check?athlete_id=XXX` endpoint
5. ✅ Check database connectivity: `/api/db-test`
6. ✅ Try "Reconnect Strava" to get fresh tokens

## Getting Your Athlete ID

To test the token-check endpoint, you need your Strava athlete ID:

1. Visit: `https://coros-fit-analysis.onrender.com/strava/status`
2. Look for `"athlete_id"` in the JSON response
3. Use that ID in the token-check URL

Example:
```
https://coros-fit-analysis.onrender.com/strava/token-check?athlete_id=123456789
```

## Local Testing

If you want to test locally and see logs in your terminal:

1. **Start the server locally:**
   ```bash
   cd fastapi_dashboard
   export $(cat .env | xargs)
   python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Watch the terminal** - all log messages will appear there

3. **Test the endpoint:**
   ```bash
   curl http://localhost:8000/strava/token-check?athlete_id=YOUR_ID
   ```

## Need More Help?

If logs don't show enough detail, you can:

1. **Enable more verbose logging** - modify `main.py` to set log level to DEBUG
2. **Add more print statements** - temporarily add `print()` statements in `strava_store.py`
3. **Check browser console** - some errors may appear in browser console (F12)
