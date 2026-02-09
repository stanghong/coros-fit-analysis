# Quick Migration: Add sport_type Column

## Problem
Error: `column activities.sport_type does not exist`

This happens because the database schema hasn't been updated with the new `sport_type` column.

## Solution: Run Migration 002

### Option 1: Supabase SQL Editor (Recommended)

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Click **"SQL Editor"** in the left sidebar
4. Click **"New query"**
5. Copy and paste the entire contents of `migrations/002_add_sport_type_column.sql`:

```sql
-- Migration: Add sport_type column to activities table
-- This allows storing Strava's sport_type separately from type for multi-sport support
-- Date: 2024

-- Add sport_type column if it doesn't exist
ALTER TABLE public.activities 
ADD COLUMN IF NOT EXISTS sport_type VARCHAR;

-- Create index on sport_type for faster filtering
CREATE INDEX IF NOT EXISTS idx_activities_sport_type ON public.activities(sport_type);

-- Backfill existing records: if type contains swim/run/ride, try to infer sport_type
-- This is a best-effort backfill for existing data
UPDATE public.activities 
SET sport_type = CASE
    WHEN LOWER(type) LIKE '%swim%' THEN 'Swim'
    WHEN LOWER(type) LIKE '%run%' THEN 'Run'
    WHEN LOWER(type) LIKE '%ride%' OR LOWER(type) LIKE '%bike%' OR LOWER(type) LIKE '%cycle%' THEN 'Ride'
    ELSE type
END
WHERE sport_type IS NULL AND type IS NOT NULL;

-- Add comment to column
COMMENT ON COLUMN public.activities.sport_type IS 'Strava sport_type field (preferred over type): Swim, Run, Ride, OpenWaterSwim, etc.';
COMMENT ON COLUMN public.activities.type IS 'Strava type field (fallback): Swim, Run, Bike, etc.';
```

6. Click **"Run"** (or press Cmd/Ctrl + Enter)
7. You should see "Success. No rows returned"

### Option 2: psql Command Line

```bash
# Set your database URL (from Render or Supabase)
export DATABASE_URL="postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres?sslmode=require"

# Run the migration
psql "$DATABASE_URL" -f fastapi_dashboard/migrations/002_add_sport_type_column.sql
```

## Verify Migration

After running the migration, verify it worked:

```sql
-- Check if column exists
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'activities' 
AND column_name = 'sport_type';
```

You should see:
```
 column_name | data_type 
-------------+-----------
 sport_type  | character varying
```

## After Migration

1. Refresh your web application
2. Click "Load Activities" again
3. The error should be gone and activities should load with sport filtering

## Notes

- The migration is **idempotent** (safe to run multiple times)
- It uses `IF NOT EXISTS` so it won't break if the column already exists
- Existing activities will be backfilled with inferred `sport_type` values
- New activities will have `sport_type` populated from Strava API
