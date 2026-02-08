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
