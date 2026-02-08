-- Migration: Add missing columns to users table
-- Date: 2024
-- Description: Adds strava_username, strava_firstname, strava_lastname, and updated_at columns
--              to users table with auto-update trigger for updated_at
-- 
-- Run this migration once using one of these methods:
--   1. Supabase SQL Editor: Copy-paste and run (recommended)
--   2. psql: psql $DATABASE_URL -f migrations/001_add_users_updated_at.sql
--
-- This migration is idempotent (safe to run multiple times).

-- Add all missing columns if they don't exist
ALTER TABLE public.users 
ADD COLUMN IF NOT EXISTS strava_username VARCHAR,
ADD COLUMN IF NOT EXISTS strava_firstname VARCHAR,
ADD COLUMN IF NOT EXISTS strava_lastname VARCHAR,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Set updated_at to created_at for existing rows (if created_at exists)
UPDATE public.users 
SET updated_at = created_at 
WHERE updated_at IS NULL AND created_at IS NOT NULL;

-- Create trigger function to auto-update updated_at on row updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop trigger if exists, then create it
DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Verify the columns were added (this will show an error if columns don't exist)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'users' 
        AND column_name = 'updated_at'
    ) THEN
        RAISE EXCEPTION 'Migration failed: updated_at column was not created';
    END IF;
    
    -- Log success (PostgreSQL doesn't have print, but we can use RAISE NOTICE in some contexts)
    -- For Supabase SQL Editor, you'll see "Success" if this completes without errors
END $$;
