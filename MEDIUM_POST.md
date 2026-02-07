# Building Strava OAuth Integration: Lessons Learned from a Real-World Implementation

## Introduction

Recently, I integrated Strava OAuth into my swimming workout analysis dashboard. What started as a simple "add Strava support" feature turned into a deep dive into OAuth flows, environment variable management, and production deployment gotchas. Here's what I learned—and what you should watch out for.

---

## What We Built

A FastAPI-based dashboard that:
- Analyzes swimming workouts from CSV files
- Connects to Strava via OAuth 2.0
- Imports and analyzes Strava activities
- Compares multiple workouts with AI-powered coaching insights

The Strava integration allows users to:
1. Connect their Strava account
2. Import swimming activities
3. Analyze individual or multiple activities
4. Get personalized coaching recommendations

---

## Key Learnings

### 1. OAuth Redirect URI Must Match Exactly

**The Problem:**
Strava rejected our OAuth requests with `"redirect_uri": "invalid"` errors.

**The Solution:**
The redirect URI must match **exactly** in three places:
- **Strava API Settings**: Authorization Callback Domain (just the domain, no protocol/path)
- **Authorization Request**: Full URL with protocol and path
- **Token Exchange Request**: Same full URL (this is often forgotten!)

**What to Watch:**
- ✅ Local: `localhost` or `127.0.0.1` (no port in callback domain)
- ✅ Production: `yourdomain.com` (no `https://` in callback domain)
- ✅ Always include `redirect_uri` in **both** authorization and token exchange requests
- ⚠️ Strava constructs the full redirect URI as: `http://[callback_domain]/[path]`

**Code Example:**
```python
# Authorization request
auth_url = f"https://www.strava.com/oauth/authorize?"
    f"client_id={CLIENT_ID}&"
    f"redirect_uri={REDIRECT_URI}&"  # Full URL
    f"response_type=code"

# Token exchange - MUST include redirect_uri!
token_response = await client.post(
    "https://www.strava.com/oauth/token",
    data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI  # ← Don't forget this!
    }
)
```

---

### 2. Environment Variables: The Devil is in the Details

**The Problem:**
`STRAVA_ENABLED` was set to `true` in Render, but the app showed `strava_enabled: false`.

**Root Causes:**
- Environment variable not set at all (most common)
- Extra whitespace: `" true "` vs `"true"`
- Case sensitivity: `"True"` vs `"true"`
- Quotes included: `"true"` vs `true`

**The Solution:**
```python
# Robust parsing
_strava_enabled_raw = os.getenv("STRAVA_ENABLED", "false").strip().lower()
STRAVA_ENABLED = _strava_enabled_raw in ("true", "1", "yes", "on")

# Debug logging
print(f"DEBUG: STRAVA_ENABLED env var = '{os.getenv('STRAVA_ENABLED', 'NOT SET')}'")
print(f"DEBUG: STRAVA_ENABLED parsed = {STRAVA_ENABLED}")
```

**What to Watch:**
- ✅ Always strip whitespace: `.strip()`
- ✅ Normalize case: `.lower()`
- ✅ Accept multiple formats: `"true"`, `"1"`, `"yes"`, `"on"`
- ✅ Add debug logging to see raw values
- ⚠️ Check Render logs after deployment to verify env vars are read correctly

---

### 3. Feature Flags: Deploy Safely, Enable Gradually

**The Strategy:**
Use feature flags to deploy new features without breaking existing functionality.

**Implementation:**
```python
# Feature flag from environment
STRAVA_ENABLED = os.getenv("STRAVA_ENABLED", "false").lower() == "true"

# Conditionally load routes
if STRAVA_ENABLED:
    try:
        from .strava_oauth import router as strava_router
        app.include_router(strava_router)
    except Exception as e:
        print(f"Warning: Strava features disabled: {e}")
        STRAVA_ENABLED = False

# Pass to frontend
return {"strava_enabled": STRAVA_ENABLED}
```

**Frontend:**
```html
{% if strava_enabled %}
<div id="stravaSection">...</div>
{% endif %}
```

**What to Watch:**
- ✅ Deploy with feature disabled first (`STRAVA_ENABLED=false`)
- ✅ Verify existing features still work
- ✅ Enable feature after confirming deployment is stable
- ✅ Use try-except to gracefully handle missing dependencies
- ⚠️ Always have a fallback if feature fails to load

---

### 4. Import Paths: Relative vs Absolute

**The Problem:**
Routes worked locally but returned "Not Found" in production.

**The Solution:**
Handle both import styles:
```python
# Try relative import first (when running as module)
try:
    from .strava_oauth import router as strava_router
except ImportError:
    # Fall back to absolute import (when running directly)
    from strava_oauth import router as strava_router
```

**What to Watch:**
- ✅ Test both `python -m uvicorn` and `uvicorn` directly
- ✅ Use relative imports for packages, absolute for scripts
- ✅ Add fallback imports for compatibility
- ⚠️ Different execution contexts (local vs production) may need different imports

---

### 5. Strava API Streams: Handle Multiple Formats

**The Problem:**
Streams API returns different formats based on `key_by_type` parameter.

**The Solution:**
```python
streams_data = streams_response.json()

if isinstance(streams_data, dict):
    # key_by_type=true returns dict
    streams = streams_data
elif isinstance(streams_data, list):
    # key_by_type=false returns list
    for stream in streams_data:
        if isinstance(stream, dict) and 'type' in stream:
            streams[stream['type']] = {
                'data': stream.get('data', []),
                'series_type': stream.get('series_type', 'time')
            }
```

**What to Watch:**
- ✅ Always check response format before parsing
- ✅ Use `key_by_type=true` for cleaner dict format
- ✅ Handle both list and dict formats gracefully
- ⚠️ Stream values might be strings, lists, or dicts—always type-check

---

### 6. Client Secret: Copy-Paste Errors

**The Problem:**
OAuth kept failing with "invalid Application" errors.

**The Root Cause:**
Client Secret had a typo: `b7ee5d76764ba...` vs `b7ee5d7674ba...` (extra "6")

**What to Watch:**
- ✅ Double-check credentials when copying from Strava
- ✅ Use "Show" button to reveal full secret
- ✅ Verify character-by-character if OAuth fails
- ⚠️ One character difference = complete failure

---

### 7. Multi-Activity Analysis: Use Timestamps for Trends

**The Insight:**
For comparing multiple workouts, use timestamps to identify trends over time.

**Implementation:**
```python
def generate_multi_workout_coach_summary(workouts, trends, time_series):
    # Identify improving/declining trends
    improving_areas = []
    declining_areas = []
    
    # Check trends over time
    if 'score' in trends:
        if trends['score']['trend'] == 'up':
            improving_areas.append(('overall performance', trends['score']['change_pct']))
    
    # Generate actionable insights
    headline = f"Your performance is improving — scores up {improvement:.1f}%"
    constraint = f"Pacing too variable — focus on consistent splits"
    action = "Next session: 8×100 on consistent splits, 20s rest"
```

**What to Watch:**
- ✅ Sort workouts by timestamp before analysis
- ✅ Compare first half vs second half to identify trends
- ✅ Prioritize declining areas for next workout focus
- ⚠️ Need at least 2 workouts for meaningful comparison

---

## Critical Deployment Checklist

### Before Deploying OAuth Features:

1. **Environment Variables**
   - [ ] All required vars set in production
   - [ ] Values are correct (no typos, no extra spaces)
   - [ ] Feature flag set appropriately (`STRAVA_ENABLED=false` initially)

2. **OAuth Configuration**
   - [ ] Client ID and Secret are correct
   - [ ] Redirect URI matches exactly in code and Strava settings
   - [ ] Authorization Callback Domain set correctly (domain only, no protocol)

3. **Strava API Settings**
   - [ ] Callback domain matches production domain
   - [ ] Full redirect URI includes protocol and path
   - [ ] Scopes requested match what's needed

4. **Code Robustness**
   - [ ] Import paths handle both relative and absolute
   - [ ] Error handling for missing dependencies
   - [ ] Graceful degradation if feature fails

5. **Testing**
   - [ ] Test locally with production-like config
   - [ ] Verify routes are registered (check logs)
   - [ ] Test OAuth flow end-to-end
   - [ ] Verify feature flag works (enable/disable)

---

## Common Pitfalls to Avoid

### ❌ Don't:
- Hardcode credentials in code
- Forget `redirect_uri` in token exchange
- Use localhost callback domain in production
- Deploy without testing feature flag
- Assume environment variables are set correctly

### ✅ Do:
- Use environment variables for all secrets
- Include `redirect_uri` in both OAuth requests
- Match callback domain exactly in Strava settings
- Deploy with feature disabled first, then enable
- Add debug logging to verify env vars
- Test both local and production configurations

---

## Debugging Tips

### When OAuth Fails:

1. **Check Environment Variables**
   ```bash
   # Add debug endpoint
   @app.get("/api/config")
   async def get_config():
       return {
           "strava_enabled": STRAVA_ENABLED,
           "debug": {
               "STRAVA_ENABLED_raw": os.getenv("STRAVA_ENABLED", "NOT_SET")
           }
       }
   ```

2. **Check Server Logs**
   - Look for: `"INFO: Strava OAuth routes loaded successfully"`
   - Check for import errors
   - Verify routes are registered

3. **Test Endpoints**
   - `/api/config` → Should show `strava_enabled: true`
   - `/strava/status` → Should work if connected
   - `/strava/login` → Should redirect to Strava

4. **Verify Strava Settings**
   - Callback domain matches production domain
   - No typos in Client ID/Secret
   - Redirect URI in code matches Strava settings

---

## Takeaways

1. **OAuth is finicky** — Every detail matters (redirect URI, callback domain, request parameters)
2. **Environment variables are tricky** — Always validate and log raw values
3. **Feature flags save you** — Deploy safely, enable gradually
4. **Import paths vary** — Handle both relative and absolute imports
5. **API formats differ** — Always check response structure before parsing
6. **Copy-paste carefully** — One character typo breaks everything
7. **Debug early and often** — Add logging to catch issues quickly

---

## Final Thoughts

Building OAuth integrations requires attention to detail. The smallest mistake—a typo, a missing parameter, or a mismatched domain—can cause complete failure. But with careful testing, robust error handling, and good debugging practices, you can build reliable integrations.

The key is to:
- Test locally first
- Deploy with feature flags
- Verify each step carefully
- Add debug logging
- Check logs after deployment

Happy coding! 🏊‍♂️

---

## Resources

- [Strava OAuth Documentation](https://developers.strava.com/docs/authentication/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OAuth 2.0 Best Practices](https://oauth.net/2/)
