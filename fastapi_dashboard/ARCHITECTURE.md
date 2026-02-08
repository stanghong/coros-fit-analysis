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
│  │  • GET  /strava/token-check → Check/refresh token         │  │
│  │                                                             │  │
│  │  Token Storage: PostgreSQL database (strava_tokens)      │  │
│  │  • Access token (encrypted in DB)                         │  │
│  │  • Refresh token (encrypted in DB)                        │  │
│  │  • Expires at timestamp                                    │  │
│  │  • Auto-refresh via ensure_valid_access_token()           │  │
│  │  • Athlete info persisted (username, firstname, lastname)  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    INGEST LAYER                            │  │
│  │  • GET  /strava/import-latest → Fetch activities (manual) │  │
│  │  • GET  /api/activities      → Get cached activities      │  │
│  │                                                             │  │
│  │  Current: Manual trigger via UI button                      │  │
│  │  • Fetches last 30 activities from Strava API              │  │
│  │  • Filters for swimming activities only                   │  │
│  │  • Upserts activities to database (activities table)       │  │
│  │  • Returns cached activities from DB                       │  │
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
│  │  Database: PostgreSQL (Supabase) with SQLAlchemy ORM       │  │
│  │                                                             │  │
│  │  Tables:                                                   │  │
│  │  • users                                                    │  │
│  │    - id (PK), strava_athlete_id (unique)                   │  │
│  │    - strava_username, strava_firstname, strava_lastname   │  │
│  │    - created_at, updated_at                                │  │
│  │                                                             │  │
│  │  • strava_tokens                                           │  │
│  │    - user_id (PK, FK), access_token, refresh_token         │  │
│  │    - expires_at (unix timestamp), scope                    │  │
│  │    - updated_at                                            │  │
│  │                                                             │  │
│  │  • activities                                               │  │
│  │    - id (PK = Strava activity ID), user_id (FK)           │  │
│  │    - type, start_date, distance_m, moving_time_s           │  │
│  │    - average_heartrate, max_heartrate                      │  │
│  │    - raw_json (full Strava API response)                   │  │
│  │    - fetched_at                                            │  │
│  │                                                             │  │
│  │  Functions (strava_store.py):                              │  │
│  │  • get_or_create_user() → Upsert user by athlete_id        │  │
│  │  • upsert_strava_token() → Store/update tokens             │  │
│  │  • ensure_valid_access_token() → Auto-refresh if expired   │  │
│  │  • upsert_activity() → Cache activities                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    SYNC LAYER                              │  │
│  │  Current: On-demand + background sync with database caching│  │
│  │  • User clicks "Load Activities" → Fetch from Strava       │  │
│  │    → Upsert to database (idempotent)                       │  │
│  │  • User clicks "Analyze" → Fetch streams from Strava      │  │
│  │  • Token refresh: Auto-refreshes expired tokens            │  │
│  │    → Updates database with new tokens                     │  │
│  │                                                             │  │
│  │  Implemented:                                              │  │
│  │  • Idempotent upserts (upsert_activity checks by ID)        │  │
│  │  • Token refresh with DB persistence                       │  │
│  │  • Retry logic with exponential backoff (strava_retry.py)  │  │
│  │  • Rate limit handling (strava_rate_limiter.py)           │  │
│  │  • Background sync job (strava_background_sync.py)        │  │
│  │  • Incremental sync (only fetch new activities)            │  │
│  │                                                             │  │
│  │  ⚠️  TODO:                                                  │  │
│  │     • Conflict resolution (activity updated on Strava)     │  │
│  │     • Webhook support for real-time updates                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                            │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐│
│  │   STRAVA API     │  │   FILE UPLOAD    │  │  SUPABASE DB  ││
│  │                  │  │                  │  │              ││
│  │  • OAuth 2.0     │  │  • CSV files     │  │  • PostgreSQL ││
│  │  • Activities    │  │  • Coros format  │  │  • Connection ││
│  │  • Streams      │  │                  │  │    Pooler     ││
│  └──────────────────┘  └──────────────────┘  └──────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Auth Layer

**What exists:**
- OAuth 2.0 flow: `/strava/login` redirects to Strava, `/strava/callback` handles the response
- Token storage in PostgreSQL database (`strava_tokens` table)
- Automatic token refresh via `ensure_valid_access_token()` (checks expiration, refreshes if needed, updates DB)
- Athlete info persistence (username, firstname, lastname stored in `users` table)
- Token check endpoint: `/strava/token-check` for debugging
- Debug endpoint: `/strava/debug/strava-athlete` to verify athlete identity

**What's missing:**
- Multi-user support (session management, user isolation)
- Secure token encryption at rest (tokens stored as plain text in DB)
- Token rotation and revocation handling
- User authentication/authorization system

**2-3 sentence summary:**
Handles Strava OAuth 2.0 authentication flow. Users click "Connect Strava" which redirects to Strava for authorization, then returns to `/strava/callback` where we exchange the code for access/refresh tokens. Tokens are persisted in PostgreSQL database (survives server restarts) and automatically refreshed when expired. Athlete identity (username, name) is fetched from Strava API and stored in the database.

---

### 2. Ingest Layer

**What exists:**
- Manual trigger: User clicks "Load Activities" button
- Fetches last 30 activities from Strava API (`/athlete/activities`)
- Filters for swimming activities (robust case-insensitive matching)
- Upserts activities to database (`activities` table) for caching
- Returns cached activities from database via `/api/activities`
- Supports pagination (per_page up to 200)
- Logs first 5 activities for debugging

**What's missing:**
- Automatic sync (webhook or polling)
- Background job to periodically fetch new activities
- Webhook endpoint to receive Strava push notifications
- Incremental sync (only fetch new activities since last sync)

**2-3 sentence summary:**
User clicks "Load Activities" which calls `/strava/import-latest` to fetch recent activities from Strava API, filters for swimming activities, and upserts them to the database for caching. Activities are stored with full Strava API response in `raw_json` field. Cached activities can be retrieved via `/api/activities` endpoint. No automatic sync exists yet - needs webhook or polling mechanism for production.

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
- PostgreSQL database (Supabase) with SQLAlchemy ORM
- Three tables: `users`, `strava_tokens`, `activities`
- Token persistence in database (survives server restarts)
- Activity caching in database (avoid re-fetching from Strava)
- Database helper functions in `strava_store.py`:
  - `get_or_create_user()` - Upsert user by athlete_id
  - `upsert_strava_token()` - Store/update OAuth tokens
  - `ensure_valid_access_token()` - Auto-refresh expired tokens
  - `upsert_activity()` - Cache activities with idempotent upserts
  - `get_activities_for_athlete_from_db()` - Retrieve cached activities
- Database connection pooling (pool_size=5, max_overflow=10)
- Auto-table creation via `DB_AUTO_CREATE=true` env var
- Migration scripts in `migrations/` directory

**What's missing:**
- Multi-user session management
- Token encryption at rest
- Database migrations tool (Alembic)
- Activity data retention policy
- Database backup strategy

**2-3 sentence summary:**
PostgreSQL database (Supabase) stores users, OAuth tokens, and cached activities. Tokens persist across server restarts and are automatically refreshed when expired. Activities are cached in the database with full Strava API response in `raw_json` field, avoiding repeated API calls. Database operations use SQLAlchemy ORM with connection pooling for efficiency.

---

### 5. Sync Layer

**What exists:**
- On-demand fetching when user clicks "Load Activities"
- On-demand stream fetching when user clicks "Analyze"
- Idempotent upserts via `upsert_activity()` (checks if activity exists by ID)
- Token refresh with database persistence (auto-updates DB on refresh)
- Retry logic with exponential backoff (`strava_retry.py`)
- Rate limit handling (`strava_rate_limiter.py`) - tracks 200/15min and 2000/day limits
- Background sync job (`strava_background_sync.py`) - periodic polling when `BACKGROUND_SYNC_ENABLED=true`
- Incremental sync - only fetches new activities since last sync timestamp
- Activity caching in database (reduces Strava API calls)
- Comprehensive error handling with retry and rate limit awareness

**What's missing:**
- Conflict resolution (what if activity updated on Strava?)
- Webhook support for real-time updates (instead of polling)
- Sync status dashboard/monitoring

**2-3 sentence summary:**
Production-ready sync layer with retry logic, rate limiting, and background jobs. When user clicks "Load Activities", activities are fetched from Strava API with automatic retries and rate limit tracking, then upserted to database (idempotent - won't create duplicates). Background sync job can run periodically to fetch new activities automatically. Incremental sync only fetches activities newer than the last sync timestamp.

---

### 6. API/UI Layer

**What exists:**
- FastAPI backend with HTML frontend
- Strava integration endpoints (`/strava/*`) - main interface
- Multi-workout comparison for Strava activities
- Feature flag system (`STRAVA_ENABLED`)
- Responsive UI with mobile support
- Interactive charts (Chart.js)
- Coach summary display (single and multi-workout)
- Real-time athlete identity display

**What's missing:**
- CSV upload (removed - Strava-only now)
- User authentication/authorization
- API versioning
- Rate limiting
- API documentation (OpenAPI/Swagger)
- Error tracking/monitoring

**2-3 sentence summary:**
FastAPI backend serves HTML dashboard focused on Strava integration. Frontend allows Strava connection, activity selection, and displays analysis results with charts and coaching insights. Feature flags control Strava visibility. Missing user auth, API docs, and monitoring for production.

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
Backend: Fetch athlete info from Strava API (/api/v3/athlete)
  ↓
Backend: get_or_create_user() → Upsert user in database
  ↓
Backend: upsert_strava_token() → Store tokens in database
  ↓
Backend: Redirect to dashboard with ?strava_connected=true
  ↓
Frontend: Shows "Import Latest Activity" button
```

---

## Current Limitations

### Production Readiness Gaps:

1. **Limited Automatic Sync**
   - ✅ Background sync job implemented (requires `BACKGROUND_SYNC_ENABLED=true`)
   - ⚠️  No webhook support (still uses polling)
   - ⚠️  Manual user action still required for on-demand sync

2. **Single User Only**
   - No session management
   - No user isolation
   - Athlete ID used as user identifier

3. **Error Recovery**
   - ✅ Retry logic with exponential backoff implemented
   - ✅ Rate limit handling implemented (200/15min, 2000/day)
   - ⚠️  Basic error messages (could be more detailed)

4. **Security Concerns**
   - Tokens stored as plain text in database (no encryption)
   - No token rotation
   - No user authentication/authorization

5. **Database**
   - ✅ Database implemented (PostgreSQL)
   - ✅ Token persistence working
   - ✅ Activity caching working
   - ⚠️  No migration tool (Alembic)
   - ⚠️  Manual SQL migrations only

---

## Next Steps (Before Adding Features)

### Priority 1: Sync Layer Improvements
- [x] Implement idempotent upserts ✅
- [x] Add retry logic with exponential backoff ✅
- [x] Handle rate limits (Strava: 200/15min, 2000/day) ✅
- [x] Background sync job (periodic polling) ✅
- [x] Incremental sync (only fetch new activities) ✅
- [ ] Conflict resolution (activity updated on Strava)
- [ ] Webhook support for real-time updates

### Priority 2: Multi-User Support
- [ ] User authentication system
- [ ] Session management
- [ ] User-scoped data access
- [ ] User isolation (prevent cross-user data access)

### Priority 3: Database Improvements
- [x] Database schema implemented ✅
- [x] Token storage working ✅
- [x] Activity caching working ✅
- [ ] Add Alembic for migrations
- [ ] Token encryption at rest
- [ ] Database backup strategy

### Priority 4: Production Hardening
- [ ] Error monitoring (Sentry, etc.)
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Rate limiting on API endpoints
- [ ] Security audit
- [ ] Performance monitoring

---

## Key Decisions Made

1. **Feature Flag Approach**: `STRAVA_ENABLED` allows safe deployment
2. **Database First**: PostgreSQL with SQLAlchemy ORM for persistence
3. **Manual Sync**: Start simple, add automation later
4. **Athlete ID as User ID**: Use Strava athlete_id as user identifier (single-user for now)
5. **On-Demand Analysis**: No pre-computation, analyze when requested
6. **Activity Caching**: Store full Strava API response in `raw_json` for flexibility
7. **Idempotent Upserts**: All database writes use upsert pattern to prevent duplicates
8. **Connection Pooling**: SQLAlchemy connection pool for efficient DB access

---

## Questions to Answer Before Scaling

1. **Storage**: How many activities per user? How long to retain?
2. **Sync Frequency**: How often to check for new activities?
3. **Rate Limits**: How to handle Strava's 200/15min limit?
4. **Users**: How many concurrent users expected?
5. **Data**: Should we store raw Strava data or only normalized?

---

This architecture represents the "thin slice" - the minimal working system. Before adding features, address the gaps in Store, Sync, and multi-user support.
