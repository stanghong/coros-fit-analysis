-- Migration script to add athlete info columns to users table
-- Run this SQL against your database to add the new columns

-- Add new columns to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS strava_username VARCHAR,
ADD COLUMN IF NOT EXISTS strava_firstname VARCHAR,
ADD COLUMN IF NOT EXISTS strava_lastname VARCHAR,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Create a trigger to automatically update updated_at on row updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop trigger if it exists, then create it
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
