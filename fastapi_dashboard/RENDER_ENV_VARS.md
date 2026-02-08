# Render Environment Variables Checklist

## Required Environment Variables

Make sure these are set in your Render service's **Environment** tab:

### Database Configuration
- ✅ `DATABASE_URL` - Your Supabase PostgreSQL connection string
  - Example: `postgresql://postgres:password@host:6543/postgres?sslmode=require`
  - **Important**: Use port `6543` (connection pooler) for Render, not `5432`
  
- ✅ `DB_AUTO_CREATE=true` - **CRITICAL**: This creates database tables on startup
  - Without this, your `users`, `strava_tokens`, and `activities` tables won't exist
  - Tokens can't be saved or retrieved without these tables

### Strava OAuth Configuration
- ✅ `STRAVA_ENABLED=true` - Enable Strava features
- ✅ `STRAVA_CLIENT_ID` - Your Strava app Client ID (e.g., `200992`)
- ✅ `STRAVA_CLIENT_SECRET` - Your Strava app Client Secret
- ✅ `STRAVA_REDIRECT_URI` - Must match your Strava app settings
  - Example: `https://coros-fit-analysis.onrender.com/strava/callback`
- ✅ `STRAVA_SCOPE` - OAuth scope (e.g., `activity:read_all`)

### Optional
- `ENV=prod` - Set to `prod` for production (dev routes will be disabled)
- `PORT` - Automatically set by Render (don't override)

## How to Set Environment Variables in Render

1. Go to your Render dashboard: https://dashboard.render.com
2. Click on your service (e.g., `coros-fit-analysis`)
3. Click on **"Environment"** tab in the left sidebar
4. Click **"Add Environment Variable"** for each variable
5. Enter the **Key** and **Value**
6. Click **"Save Changes"**
7. Render will automatically redeploy your service

## Verification

After setting environment variables, check your logs to confirm:

1. **Database tables created:**
   ```
   INFO: Database tables auto-created
   ```

2. **Strava enabled:**
   ```
   DEBUG: STRAVA_ENABLED parsed = True
   INFO: Strava OAuth routes loaded successfully
   ```

3. **Test endpoints:**
   - `/api/db-test` - Should return `{"db_connected": true}`
   - `/api/db-status` - Should show `{"tables_exist": true}`
   - `/api/config` - Should show `{"strava_enabled": true}`

## Common Issues

### Issue: "DB_AUTO_CREATE not set to true"
**Symptom:** Logs show "Skipping automatic table creation"
**Fix:** Add `DB_AUTO_CREATE=true` to environment variables

### Issue: "Database not available"
**Symptom:** `/api/db-test` returns `{"db_connected": false}`
**Fix:** 
- Check `DATABASE_URL` is set correctly
- Use connection pooler (port 6543) for Supabase
- URL-encode special characters in password (e.g., `@` becomes `%40`)

### Issue: "Strava OAuth routes not loaded"
**Symptom:** `/strava/login` returns 404
**Fix:**
- Set `STRAVA_ENABLED=true`
- Verify `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` are set
- Check logs for import errors

## Quick Checklist

Before testing Strava integration, verify:

- [ ] `DATABASE_URL` is set and correct
- [ ] `DB_AUTO_CREATE=true` is set
- [ ] `STRAVA_ENABLED=true` is set
- [ ] `STRAVA_CLIENT_ID` is set
- [ ] `STRAVA_CLIENT_SECRET` is set
- [ ] `STRAVA_REDIRECT_URI` matches your Strava app settings
- [ ] `STRAVA_SCOPE` is set (usually `activity:read_all`)
- [ ] Service has been redeployed after setting variables
- [ ] Logs show "Database tables auto-created"
- [ ] Logs show "Strava OAuth routes loaded successfully"
