# Render Database Connection Troubleshooting

## Error: "Network is unreachable"

This error typically occurs when:
1. DATABASE_URL is not set in Render environment variables
2. DATABASE_URL is incorrect or malformed
3. Supabase connection restrictions (IP allowlist)
4. SSL mode not properly configured

## Solution Steps

### 1. Verify DATABASE_URL in Render

Go to your Render service → Environment → Check:
- `DATABASE_URL` is set
- Value matches your Supabase connection string exactly
- Password is URL-encoded (e.g., `@` becomes `%40`)

**Correct format:**
```
postgresql://postgres:[PASSWORD]@[PROJECT].supabase.co:5432/postgres?sslmode=require
```

### 2. Check Supabase Connection Settings

In Supabase Dashboard:
- Go to Settings → Database
- Check "Connection Pooling" settings
- Verify "Allowed IPs" - Render IPs should be allowed (or set to allow all)
- Check if "Direct connection" is enabled

### 3. Use Connection Pooling (Recommended)

Supabase provides a connection pooler that works better with Render:

**Instead of:**
```
postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
```

**Use:**
```
postgresql://postgres:password@db.xxx.supabase.co:6543/postgres?sslmode=require
```

Port `6543` is the connection pooler (better for serverless/cloud deployments).

### 4. Verify SSL Mode

Ensure `?sslmode=require` is in your DATABASE_URL:
```
postgresql://postgres:password@db.xxx.supabase.co:5432/postgres?sslmode=require
```

### 5. Test Connection String

You can test the connection string locally first:
```bash
psql "postgresql://postgres:password@db.xxx.supabase.co:5432/postgres?sslmode=require"
```

### 6. Check Render Logs

In Render Dashboard:
- Go to your service → Logs
- Look for startup messages about database connection
- Check for any error messages during app startup

### 7. Common Issues

**Issue:** Password contains special characters
**Fix:** URL-encode special characters:
- `@` → `%40`
- `#` → `%23`
- `%` → `%25`

**Issue:** IPv6 address in error (like `2600:1f18:...`)
**Fix:** Supabase might be resolving to IPv6. Try:
- Use connection pooler port (6543)
- Or ensure Render supports IPv6 connections

**Issue:** Connection timeout
**Fix:** 
- Use connection pooler (port 6543)
- Increase connection pool settings
- Check Supabase firewall rules

## Quick Fix Checklist

- [ ] DATABASE_URL is set in Render environment variables
- [ ] Password is URL-encoded
- [ ] `?sslmode=require` is included
- [ ] Using correct Supabase project URL
- [ ] Supabase allows connections from Render IPs
- [ ] Try connection pooler port (6543) instead of direct (5432)

## Alternative: Use Supabase Connection Pooler

The connection pooler is more reliable for cloud deployments:

1. In Supabase Dashboard → Settings → Database
2. Find "Connection Pooling" section
3. Use the "Transaction" mode connection string
4. It will use port `6543` instead of `5432`
5. Update DATABASE_URL in Render with this connection string

Example:
```
postgresql://postgres.xxx:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres?sslmode=require
```
