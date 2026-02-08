# Local Database Testing Guide

## Quick Test Steps

### 1. Stop any running server
```bash
# Find and stop the server on port 8000
lsof -ti:8000 | xargs kill
```

### 2. Set environment variables
```bash
cd fastapi_dashboard

export DATABASE_URL="postgresql://postgres:1Lstjls%40baco@db.gomnffxjxiktwniqqwsc.supabase.co:5432/postgres?sslmode=require"
export DB_AUTO_CREATE=true
```

### 3. Start the server
```bash
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO: Database tables auto-created
INFO: Database engine created successfully
```

### 4. Test endpoints (in another terminal)

#### Test database connection:
```bash
curl http://localhost:8000/api/db-test
```

Expected response:
```json
{"db_connected": true}
```

#### Check database status:
```bash
curl http://localhost:8000/api/db-status
```

Expected response:
```json
{
  "tables_exist": true,
  "user_count": 0,
  "existing_tables": ["users", "strava_tokens", "activities"]
}
```

#### Test health endpoint:
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "ok",
  "message": "Swimming Dashboard API is running"
}
```

## Alternative: Use the test script

```bash
cd fastapi_dashboard
./test_db_local.sh
```

This script will:
1. Test the database connection
2. Start the server with proper environment variables
3. Show you the endpoints to test

## What to Verify

✅ **Database Connection**: `/api/db-test` returns `{"db_connected": true}`

✅ **Tables Created**: `/api/db-status` shows `"tables_exist": true`

✅ **Server Running**: `/api/health` returns success

✅ **No Errors**: Check server logs for any warnings or errors

## Troubleshooting

### If `db_connected: false`
- Check that `DATABASE_URL` is set correctly
- Verify the Supabase database is accessible
- Check password encoding (special characters like `@` must be `%40`)

### If tables don't exist
- Ensure `DB_AUTO_CREATE=true` is set
- Check server startup logs for "Database tables auto-created"
- Manually verify in Supabase dashboard

### If port 8000 is in use
```bash
# Find what's using port 8000
lsof -ti:8000

# Kill it
kill <PID>

# Or use a different port
uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

## Next Steps After Testing

Once database connectivity is confirmed:
1. Test Strava OAuth flow (if `STRAVA_ENABLED=true`)
2. Test activity caching endpoints
3. Verify token persistence
