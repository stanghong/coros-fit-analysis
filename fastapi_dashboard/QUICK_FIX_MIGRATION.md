# Quick Fix: Add Missing Database Columns

## The Problem
Error: `column users.updated_at does not exist`

The database table is missing the new columns we added to the User model.

## Solution: Run This SQL in Supabase

1. **Go to Supabase Dashboard:**
   - Visit: https://supabase.com/dashboard
   - Select your project
   - Click "SQL Editor" in the left sidebar

2. **Paste and Run This SQL:**

```sql
-- Add missing columns to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS strava_username VARCHAR,
ADD COLUMN IF NOT EXISTS strava_firstname VARCHAR,
ADD COLUMN IF NOT EXISTS strava_lastname VARCHAR,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Create trigger function for auto-updating updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

3. **Click "Run" button**

4. **Verify it worked:**
   - You should see "Success. No rows returned"
   - Or check with: `SELECT column_name FROM information_schema.columns WHERE table_name = 'users';`
   - You should see: `strava_username`, `strava_firstname`, `strava_lastname`, `updated_at`

5. **Restart Render service** (or wait for auto-redeploy)

6. **Test again:**
   - Click "Load Activities" - it should work now!

## That's It!

After running this SQL, the error should be gone and "Load Activities" should work.
