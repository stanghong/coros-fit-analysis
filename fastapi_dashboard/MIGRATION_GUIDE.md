# Database Migration Guide

## Problem
The error `column users.updated_at does not exist` occurs because the database tables were created before we added the `updated_at` column to the User model.

## Quick Fix: Run This Migration Once

### Recommended: Supabase SQL Editor

1. **Go to Supabase Dashboard:**
   - Visit: https://supabase.com/dashboard
   - Select your project
   - Click "SQL Editor" in the left sidebar

2. **Copy and paste the migration SQL:**
   - Open `migrations/001_add_users_updated_at.sql`
   - Copy the entire contents
   - Paste into Supabase SQL Editor
   - Click "Run"

3. **Verify it worked:**
   - You should see "Success" message
   - The error should be gone after restarting your app

### Alternative: psql Command Line

```bash
# Set your database URL
export DATABASE_URL="postgresql://user:pass@host:port/dbname?sslmode=require"

# Run the migration
psql "$DATABASE_URL" -f fastapi_dashboard/migrations/001_add_users_updated_at.sql
```

## Migration Files

All migration scripts are in the `migrations/` directory:
- `001_add_users_updated_at.sql` - Adds `updated_at` column to `users` table

See `migrations/README.md` for more details.

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
