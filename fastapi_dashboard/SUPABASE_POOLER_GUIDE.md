# How to Get Supabase Connection Pooler URL

## The Problem
Render (and many cloud platforms) cannot connect to Supabase's direct connection (port 5432) because:
- IPv6 compatibility issues
- Network restrictions
- Connection limits

## Solution: Use Connection Pooler

The connection pooler uses port **6543** and works reliably with Render.

## Steps to Get Pooler Connection String

### Option 1: From Connection String Tab

1. In Supabase Dashboard → Settings → Database
2. Click on **"Connection String"** tab
3. Look for dropdown menus:
   - **Type**: Keep as "URI"
   - **Source**: Change from "Primary Database" to **"Connection Pooler"** or **"Session Pooler"**
   - **Method**: Should show "Session mode" or "Transaction mode"
4. Copy the connection string shown (it will use port **6543**)

### Option 2: From Pooler Settings

1. In Supabase Dashboard → Settings → Database
2. Click **"Pooler settings"** button (you mentioned seeing this)
3. Look for connection strings or endpoints
4. Find the connection string that uses port **6543**

### Option 3: Manual Construction

If you can't find the pooler connection string, you can construct it:

**Format:**
```
postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
```

**Steps:**
1. Get your project reference from your direct connection URL:
   - Direct: `db.gomnffxjxiktwniqqwsc.supabase.co`
   - Project ref: `gomnffxjxiktwniqqwsc`

2. Determine your region (check Supabase dashboard or use common ones):
   - US West: `us-west-1`
   - US East: `us-east-1`
   - EU: `eu-west-1`
   - Asia: `ap-southeast-1`

3. Construct the pooler URL:
   ```
   postgresql://postgres.gomnffxjxiktwniqqwsc:1Lstjls%40baco@aws-0-us-west-1.pooler.supabase.com:6543/postgres?sslmode=require
   ```

### Option 4: Check Supabase Docs

1. Go to Supabase Dashboard
2. Click "Docs" button (you mentioned seeing this)
3. Search for "Connection Pooling" or "Session Pooler"
4. Follow instructions to get the connection string

## What to Look For

✅ **Good (Pooler):**
- Port: **6543**
- Host: Contains `pooler.supabase.com`
- Example: `aws-0-us-west-1.pooler.supabase.com:6543`

❌ **Bad (Direct - won't work on Render):**
- Port: **5432**
- Host: `db.xxx.supabase.co:5432`
- Warning: "Not IPv4 compatible"

## Quick Test

Once you have the pooler connection string:

1. Update `DATABASE_URL` in Render with the pooler URL
2. Test: `https://coros-fit-analysis.onrender.com/api/db-test`
3. Should return: `{"db_connected": true}`

## Alternative: IPv4 Add-on

If you must use direct connection:
- Click "IPv4 add-on" button in Supabase
- This enables IPv4 support (may have additional cost)
- Then direct connection (port 5432) should work

But **connection pooler is recommended** - it's free and more reliable for cloud deployments.
