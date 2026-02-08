#!/bin/bash
# Quick database test script

echo "=== Database Connectivity Test ==="
echo ""

# Step 1: Stop any existing server
echo "1. Stopping any server on port 8000..."
lsof -ti:8000 | xargs kill 2>/dev/null || echo "   No server running"
sleep 1

# Step 2: Set environment
echo "2. Setting environment variables..."
export DATABASE_URL="postgresql://postgres:1Lstjls%40baco@db.gomnffxjxiktwniqqwsc.supabase.co:5432/postgres?sslmode=require"
export DB_AUTO_CREATE=true

# Step 3: Test Python connection
echo "3. Testing Python database connection..."
python3 -c "
import sys
sys.path.insert(0, 'backend')
from db import test_db_connection
success, error = test_db_connection()
if success:
    print('   ✅ Database connection: SUCCESS')
else:
    print(f'   ❌ Database connection: FAILED')
    print(f'   Error: {error}')
    sys.exit(1)
" || exit 1

# Step 4: Start server in background
echo "4. Starting FastAPI server..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > /tmp/fastapi_test.log 2>&1 &
SERVER_PID=$!
echo "   Server PID: $SERVER_PID"
sleep 3

# Step 5: Test endpoints
echo "5. Testing endpoints..."
echo ""
echo "   /api/db-test:"
curl -s http://localhost:8000/api/db-test | python3 -m json.tool || echo "   ❌ Failed"
echo ""
echo "   /api/db-status:"
curl -s http://localhost:8000/api/db-status | python3 -m json.tool || echo "   ❌ Failed"
echo ""
echo "   /api/health:"
curl -s http://localhost:8000/api/health | python3 -m json.tool || echo "   ❌ Failed"

# Step 6: Cleanup
echo ""
echo "6. Stopping server..."
kill $SERVER_PID 2>/dev/null
echo "   ✅ Test complete!"
echo ""
echo "Server logs saved to: /tmp/fastapi_test.log"
