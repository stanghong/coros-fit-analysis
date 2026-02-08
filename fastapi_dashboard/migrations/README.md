# Database Migrations

This directory contains SQL migration scripts for the database schema.

## Current Migrations

### 001_add_users_updated_at.sql
**Problem:** `column users.updated_at does not exist`  
**Solution:** Adds `updated_at` timestamp column to `users` table with auto-update trigger.

## How to Run Migrations

### Method 1: Supabase SQL Editor (Recommended)

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Click "SQL Editor" in the left sidebar
4. Copy the contents of the migration file (e.g., `001_add_users_updated_at.sql`)
5. Paste into the SQL editor
6. Click "Run"

### Method 2: psql Command Line

```bash
# Set your database URL
export DATABASE_URL="postgresql://user:pass@host:port/dbname?sslmode=require"

# Run the migration
psql "$DATABASE_URL" -f migrations/001_add_users_updated_at.sql
```

### Method 3: Python Script (if available)

Some migrations may have corresponding Python scripts in `backend/` directory.

## Migration Order

Run migrations in numerical order:
- `001_*.sql` first
- `002_*.sql` second
- etc.

## Safety

All migrations use `IF NOT EXISTS` and are **idempotent** - safe to run multiple times.

## Verification

After running a migration, verify it worked:

```sql
-- Check if column exists
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name = 'updated_at';
```

## Troubleshooting

- **Permission errors:** Ensure your database user has `ALTER TABLE` permissions
- **Column already exists:** This is fine - migrations are idempotent
- **Connection errors:** Check your `DATABASE_URL` and network connectivity
