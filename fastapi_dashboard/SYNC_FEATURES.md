# Strava Sync Layer Features

This document describes the sync layer features implemented for Strava activity synchronization.

## Features Implemented

### 1. Retry Logic with Exponential Backoff ✅

**File:** `backend/strava_retry.py`

- Automatically retries failed API calls with exponential backoff
- Handles retryable errors: 429 (rate limit), 500, 502, 503, 504
- Network errors are always retried
- Configurable:
  - `MAX_RETRIES = 3` (default)
  - `INITIAL_BACKOFF = 1` second
  - `MAX_BACKOFF = 60` seconds
  - `BACKOFF_MULTIPLIER = 2`

**Usage:**
```python
from strava_retry import retry_with_backoff

async def fetch_data():
    return await client.get(url, headers=headers)

response = await retry_with_backoff(fetch_data, description="Fetching activities")
```

### 2. Rate Limit Handling ✅

**File:** `backend/strava_rate_limiter.py`

- Tracks API calls: 200 per 15 minutes, 2000 per day
- Prevents API calls when limits are exceeded
- Provides status endpoint for monitoring

**Strava Limits:**
- 200 requests per 15 minutes
- 2000 requests per day

**Usage:**
```python
from strava_rate_limiter import check_rate_limit, record_api_call, get_rate_limit_status

# Check before making call
can_proceed, error_msg = check_rate_limit()
if not can_proceed:
    raise ValueError(error_msg)

# Record after successful call
record_api_call()

# Check status
status = get_rate_limit_status()
```

**Endpoint:**
- `GET /strava/rate-limit-status` - Returns current rate limit status

### 3. Background Sync Job ✅

**File:** `backend/strava_background_sync.py`

- Periodically syncs activities for all connected users
- Runs every 60 minutes (configurable via `SYNC_INTERVAL_MINUTES`)
- Respects rate limits (pauses if limit is low)
- Syncs users in batches with delays between users

**Configuration:**
- Set `BACKGROUND_SYNC_ENABLED=true` in environment variables
- Job starts automatically on FastAPI startup
- Job stops on FastAPI shutdown

**Behavior:**
- Only syncs users with valid Strava tokens
- Uses incremental sync (only new activities)
- Limits to 3 pages per user to respect rate limits
- Waits 10 seconds between users

### 4. Incremental Sync ✅

**File:** `backend/strava_sync.py`

- Only fetches activities newer than the last sync
- Uses the most recent activity's `start_date` as the sync point
- Stops fetching when it reaches activities older than last sync
- Supports multi-page fetching

**Usage:**
```python
from strava_sync import sync_activities

result = await sync_activities(
    db=db,
    athlete_id=athlete_id,
    limit=30,
    incremental=True,  # Only fetch new activities
    max_pages=10
)
```

**Benefits:**
- Faster syncs (only new data)
- Reduces API calls
- Respects rate limits better

## New Endpoints

### `POST /strava/sync`

Manually trigger sync for a user.

**Query Parameters:**
- `athlete_id` (required): Strava athlete ID
- `incremental` (optional, default: true): Only fetch new activities
- `limit` (optional, default: 30): Activities per page
- `max_pages` (optional, default: 10): Maximum pages to fetch

**Response:**
```json
{
  "status": "success",
  "synced_count": 30,
  "new_count": 5,
  "updated_count": 25,
  "pages_fetched": 1,
  "rate_limit_status": {
    "requests_15min": 10,
    "requests_day": 150,
    "remaining_15min": 190,
    "remaining_day": 1850
  }
}
```

### `GET /strava/rate-limit-status`

Get current rate limit status.

**Response:**
```json
{
  "requests_15min": 10,
  "requests_day": 150,
  "remaining_15min": 190,
  "remaining_day": 1850,
  "reset_15min_seconds": 300,
  "reset_day_seconds": 82800
}
```

## Updated Endpoints

### `GET /strava/import-latest`

Now uses the sync service with:
- Retry logic
- Rate limiting
- Incremental sync support (via `?incremental=true` parameter)

**Backward Compatible:**
- Falls back to old method if sync service unavailable
- Works with or without `athlete_id` parameter

## Configuration

### Environment Variables

```bash
# Enable background sync job
BACKGROUND_SYNC_ENABLED=true

# Sync interval (in minutes, default: 60)
SYNC_INTERVAL_MINUTES=60
```

### Rate Limiter Configuration

Edit `strava_rate_limiter.py`:
```python
RATE_LIMIT_15MIN = 200  # Requests per 15 minutes
RATE_LIMIT_DAY = 2000   # Requests per day
```

### Retry Configuration

Edit `strava_retry.py`:
```python
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
MAX_BACKOFF = 60     # seconds
BACKOFF_MULTIPLIER = 2
```

## Architecture

```
┌─────────────────────────────────────────┐
│         API Endpoints                    │
│  /strava/sync, /strava/import-latest   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      strava_sync.py                     │
│  - Incremental sync logic               │
│  - Coordinates retry + rate limiting    │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌──────────────┐  ┌──────────────┐
│ strava_retry │  │ rate_limiter │
│ - Exponential│  │ - Track calls│
│   backoff    │  │ - Enforce    │
│              │  │   limits     │
└──────────────┘  └──────────────┘
```

## Production Considerations

### Rate Limiter Storage

Currently uses in-memory storage. For production:
- Use Redis for distributed rate limiting
- Or store in database with cleanup job

### Background Sync

- Runs in the same process as FastAPI
- For production, consider:
  - Separate worker process
  - Celery or similar task queue
  - Kubernetes CronJob

### Error Handling

- All sync operations log errors
- Failed activities are skipped (not blocking)
- Rate limit errors are surfaced to user

## Testing

Test the sync endpoint:
```bash
curl -X POST "http://localhost:8000/strava/sync?athlete_id=17449842&incremental=true"
```

Check rate limit status:
```bash
curl "http://localhost:8000/strava/rate-limit-status"
```

## Next Steps

- [ ] Add Redis for distributed rate limiting
- [ ] Add webhook support for real-time sync
- [ ] Add sync status tracking in database
- [ ] Add sync history/audit log
- [ ] Add admin dashboard for sync monitoring
