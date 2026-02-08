# Database Migration Guide

## Problem
The error `column users.strava_username does not exist` occurs because the database tables were created before we added new columns to the User model.

## Solution: Add Missing Columns

### Option 1: Automatic Migration (Recommended)

The migration will run automatically when `DB_AUTO_CREATE=true` is set and the app starts.

1. **On Render:**
   - Make sure `DB_AUTO_CREATE=true` is set in environment variables
   - Redeploy your service (or it will auto-deploy after the code push)
   - Check logs - you should see: `✅ Migration completed successfully!`

### Option 2: Manual SQL Migration

If you prefer to run the migration manually:

1. **Go to Supabase Dashboard:**
   - Visit: https://supabase.com/dashboard
   - Select your project
   - Go to "SQL Editor"

2. **Run this SQL:**
   ```sql
   -- Add new columns to users table
   ALTER TABLE users 
   ADD COLUMN IF NOT EXISTS strava_username VARCHAR,
   ADD COLUMN IF NOT EXISTS strava_firstname VARCHAR,
   ADD COLUMN IF NOT EXISTS strava_lastname VARCHAR,
   ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

   -- Create trigger function for updated_at
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

3. **Click "Run"**

### Option 3: Run Python Migration Script Locally

If you have local database access:

```bash
cd fastapi_dashboard
export DATABASE_URL="your_database_url_here"
python -m backend.migrate_add_athlete_info
```

## Verify Migration

After migration, verify the columns exist:

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN ('strava_username', 'strava_firstname', 'strava_lastname', 'updated_at');
```

You should see all 4 columns listed.

## After Migration

1. **Restart your Render service** (if using automatic migration)
2. **Reconnect Strava** - Click "Reconnect Strava" to trigger OAuth and save athlete info
3. **Test** - Click "Load Activities" - it should work now!

## Troubleshooting

- **If migration fails:** Check that you have ALTER TABLE permissions
- **If columns still missing:** Make sure you're connected to the correct database
- **If errors persist:** Check Render logs for detailed error messages
