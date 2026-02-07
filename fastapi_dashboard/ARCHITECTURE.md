# Thin Slice Architecture: Current State

## System Overview

This document describes the current architecture of the Swimming Workout Dashboard with Strava integration. This is a "thin slice" - the minimal working implementation before adding more features.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Upload CSV   │  │ Connect      │  │ View Results │          │
│  │              │  │ Strava       │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND (Render)                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API/UI LAYER                          │  │
│  │  • GET  /                    → Dashboard HTML             │  │
│  │  • POST /api/analyze         → Analyze CSV file          │  │
│  │  • POST /api/compare         → Compare multiple CSVs      │  │
│  │  • GET  /api/config          → Feature flags             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    AUTH LAYER                              │  │
│  │  • GET  /strava/login       → Redirect to Strava OAuth   │  │
│  │  • GET  /strava/callback    → Handle OAuth callback       │  │
│  │  • GET  /strava/status      → Check connection status     │  │
│  │                                                             │  │
│  │  Token Storage: In-memory dict (strava_tokens)             │  │
│  │  • Access token                                           │  │
│  │  • Refresh token                                           │  │
│  │  • Expires at timestamp                                    │  │
│  │  • Athlete info                                            │  │
│  │                                                             │  │
│  │  ⚠️  TODO: Move to database for production                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    INGEST LAYER                            │  │
│  │  • GET  /strava/import-latest → Fetch activities (manual) │  │
│  │                                                             │  │
│  │  Current: Manual trigger via UI button                      │  │
│  │  • Fetches last 30 activities from Strava API              │  │
│  │  • Filters for swimming activities only                   │  │
│  │                                                             │  │
│  │  ⚠️  TODO: Add webhook or polling for automatic sync       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    NORMALIZE LAYER                         │  │
│  │  strava_converter.py                                       │  │
│  │  • strava_streams_to_dataframe()                          │  │
│  │    - Converts Strava activity + streams → DataFrame        │  │
│  │    - Maps Strava fields to internal swim model             │  │
│  │    - Handles missing stream data gracefully               │  │
│  │                                                             │  │
│  │  Internal Model:                                           │  │
│  │  • session_start_time, session_total_distance             │  │
│  │  • enhanced_speed, cadence, heart_rate (time-series)        │  │
│  │  • Matches CSV format from Coros devices                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    ANALYSIS LAYER                            │  │
│  │  analysis_engine.py                                       │  │
│  │  • analyze_workout() → Single workout analysis            │  │
│  │  • calculate_swim_metrics() → Metrics calculation          │  │
│  │  • generate_coach_summary() → Coaching insights            │  │
│  │                                                             │  │
│  │  comparison_engine.py                                     │  │
│  │  • analyze_multiple_workouts() → Multi-workout comparison │  │
│  │  • generate_multi_workout_coach_summary() → Trends        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    STORE LAYER                             │  │
│  │  Current: In-memory storage                                │  │
│  │  • strava_tokens: Dict[str, Dict]                        │  │
│  │    - Key: "default_user" (single-user demo)               │  │
│  │    - Value: {access_token, refresh_token, expires_at, ...} │  │
│  │                                                             │  │
│  │  ⚠️  TODO: Database tables needed:                       │  │
│  │     • users (id, email, created_at)                        │  │
│  │     • strava_tokens (user_id, access_token, refresh_token,│  │
│  │       expires_at, athlete_info)                            │  │
│  │     • activities (id, user_id, strava_activity_id,        │  │
│  │       normalized_data, analyzed_data, created_at)         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    SYNC LAYER                              │  │
│  │  Current: On-demand fetch (no sync)                       │  │
│  │  • User clicks "Load Activities" → Fetch from Strava       │  │
│  │  • User clicks "Analyze" → Fetch streams                 │  │
│  │                                                             │  │
│  │  ⚠️  TODO: Implement sync layer:                           │  │
│  │     • Idempotent upserts (check if activity exists)        │  │
│  │     • Retry logic for failed API calls                     │  │
│  │     • Background job to sync new activities                │  │
│  │     • Handle rate limits (200/15min, 2000/day)            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                            │
│                                                                  │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │   STRAVA API     │         │   FILE UPLOAD    │             │
│  │                  │         │                  │             │
│  │  • OAuth 2.0     │         │  • CSV files     │             │
│  │  • Activities    │         │  • Coros format  │             │
│  │  • Streams      │         │                  │             │
│  └──────────────────┘         └──────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Auth Layer

**What exists:**
- OAuth 2.0 flow: `/strava/login` redirects to Strava, `/strava/callback` handles the response
- Token storage in-memory dictionary (`strava_tokens`)
- Basic token refresh logic (checks expiration, refreshes if needed)
- Single-user demo mode (hardcoded `"default_user"`)

**What's missing:**
- Database-backed token storage (currently lost on server restart)
- Multi-user support (session management)
- Secure token encryption at rest
- Token rotation and revocation handling

**2-3 sentence summary:**
Handles Strava OAuth 2.0 authentication flow. Users click "Connect Strava" which redirects to Strava for authorization, then returns to `/strava/callback` where we exchange the code for access/refresh tokens. Tokens are currently stored in-memory (lost on restart) and need to be moved to a database for production.

---

### 2. Ingest Layer

**What exists:**
- Manual trigger: User clicks "Load Activities" button
- Fetches last 30 activities from Strava API (`/athlete/activities`)
- Filters for swimming activities only
- Displays list in UI for user selection

**What's missing:**
- Automatic sync (webhook or polling)
- Background job to periodically fetch new activities
- Webhook endpoint to receive Strava push notifications
- Incremental sync (only fetch new activities since last sync)

**2-3 sentence summary:**
Currently manual - user clicks "Load Activities" which calls `/strava/import-latest` to fetch recent activities from Strava API. Returns list of swimming activities for user to select. No automatic sync exists yet - needs webhook or polling mechanism for production.

---

### 3. Normalize Layer

**What exists:**
- `strava_converter.py` with `strava_streams_to_dataframe()` function
- Converts Strava activity summary + streams to pandas DataFrame
- Maps Strava fields to internal swim model format:
  - `velocity_smooth` → `speed` / `enhanced_speed`
  - `cadence` → `cadence` (strokes/min)
  - `distance` → `distance` (meters)
  - Activity summary → session metadata columns
- Handles missing stream data gracefully (creates minimal DataFrame)

**What's missing:**
- Validation of data quality
- Handling different activity types (currently only swimming)
- Unit conversion utilities
- Data quality scoring

**2-3 sentence summary:**
Converts Strava API responses (activity summary + time-series streams) into our internal DataFrame format that matches CSV structure from Coros devices. Maps Strava-specific fields (`velocity_smooth`, `cadence`) to our standard columns (`enhanced_speed`, `cadence`). Handles missing data by creating minimal DataFrames from activity summaries when streams aren't available.

---

### 4. Store Layer

**What exists:**
- In-memory Python dictionary for tokens: `strava_tokens["default_user"]`
- No database - all data is ephemeral
- Activities are fetched on-demand, not stored

**What's missing:**
- Database schema (users, tokens, activities tables)
- Persistent storage for tokens (survives server restarts)
- Activity caching (avoid re-fetching from Strava)
- User session management

**2-3 sentence summary:**
Currently no persistent storage - tokens stored in-memory dictionary, activities fetched on-demand and not cached. This means tokens are lost on server restart and we re-fetch activities every time. Need database tables for users, tokens, and activities to make this production-ready.

---

### 5. Sync Layer

**What exists:**
- On-demand fetching when user clicks "Load Activities"
- On-demand stream fetching when user clicks "Analyze"
- Basic error handling (shows error message if API call fails)

**What's missing:**
- Idempotent upserts (check if activity already exists before storing)
- Retry logic with exponential backoff
- Background sync job (periodic polling or webhook processing)
- Rate limit handling (Strava: 200/15min, 2000/day)
- Conflict resolution (what if activity updated on Strava?)

**2-3 sentence summary:**
No automated sync - everything is on-demand when user clicks buttons. No idempotency checks, retry logic, or background jobs. Need to implement proper sync layer with idempotent upserts, retry logic, and rate limit handling for production use.

---

### 6. API/UI Layer

**What exists:**
- FastAPI backend with HTML frontend
- CSV upload and analysis (`/api/analyze`)
- Multi-workout comparison (`/api/compare`)
- Strava integration endpoints (`/strava/*`)
- Feature flag system (`STRAVA_ENABLED`)
- Responsive UI with mobile support
- Interactive charts (Chart.js)
- Coach summary display (single and multi-workout)

**What's missing:**
- User authentication/authorization
- API versioning
- Rate limiting
- API documentation (OpenAPI/Swagger)
- Error tracking/monitoring

**2-3 sentence summary:**
FastAPI backend serves HTML dashboard and REST API endpoints. Frontend allows CSV upload, Strava connection, and displays analysis results with charts and coaching insights. Feature flags control Strava visibility. Missing user auth, API docs, and monitoring for production.

---

## Data Flow Examples

### Example 1: Analyze Strava Activity

```
User clicks "Analyze" on activity
  ↓
Frontend: POST /strava/analyze-activity/{id}
  ↓
Backend: Fetch activity details from Strava API
  ↓
Backend: Fetch activity streams from Strava API
  ↓
Normalize: strava_streams_to_dataframe() converts to DataFrame
  ↓
Analysis: analyze_workout() processes DataFrame
  ↓
Response: Returns analysis results (metrics, scores, insights)
  ↓
Frontend: displayResults() shows charts and coach summary
```

### Example 2: OAuth Flow

```
User clicks "Connect Strava"
  ↓
Frontend: Redirect to /strava/login
  ↓
Backend: Redirect to Strava OAuth URL
  ↓
User authorizes on Strava
  ↓
Strava redirects to /strava/callback?code=...
  ↓
Backend: Exchange code for tokens (POST to Strava)
  ↓
Backend: Store tokens in-memory (strava_tokens dict)
  ↓
Backend: Redirect to dashboard with ?strava_connected=true
  ↓
Frontend: Shows "Import Latest Activity" button
```

---

## Current Limitations

### Production Readiness Gaps:

1. **No Database**
   - Tokens lost on restart
   - No activity caching
   - No user management

2. **No Automatic Sync**
   - Manual user action required
   - No background jobs
   - No webhook support

3. **Single User Only**
   - Hardcoded `"default_user"`
   - No session management
   - No user isolation

4. **No Error Recovery**
   - No retry logic
   - No rate limit handling
   - No idempotency

5. **Security Concerns**
   - Tokens in plain memory
   - No encryption
   - No token rotation

---

## Next Steps (Before Adding Features)

### Priority 1: Database Layer
- [ ] Design schema (users, tokens, activities)
- [ ] Choose database (PostgreSQL recommended)
- [ ] Implement token storage
- [ ] Add activity caching

### Priority 2: Sync Layer
- [ ] Implement idempotent upserts
- [ ] Add retry logic with backoff
- [ ] Handle rate limits
- [ ] Background sync job

### Priority 3: Multi-User Support
- [ ] User authentication
- [ ] Session management
- [ ] User-scoped data access

### Priority 4: Production Hardening
- [ ] Error monitoring
- [ ] API documentation
- [ ] Rate limiting
- [ ] Security audit

---

## Key Decisions Made

1. **Feature Flag Approach**: `STRAVA_ENABLED` allows safe deployment
2. **In-Memory First**: Quick prototype, but needs DB for production
3. **Manual Sync**: Start simple, add automation later
4. **Single User Demo**: Proof of concept, expand to multi-user later
5. **On-Demand Analysis**: No pre-computation, analyze when requested

---

## Questions to Answer Before Scaling

1. **Storage**: How many activities per user? How long to retain?
2. **Sync Frequency**: How often to check for new activities?
3. **Rate Limits**: How to handle Strava's 200/15min limit?
4. **Users**: How many concurrent users expected?
5. **Data**: Should we store raw Strava data or only normalized?

---

This architecture represents the "thin slice" - the minimal working system. Before adding features, address the gaps in Store, Sync, and multi-user support.
