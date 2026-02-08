#!/bin/bash
# Test database connectivity locally

cd "$(dirname "$0")"

export DATABASE_URL="postgresql://postgres:1Lstjls%40baco@db.gomnffxjxiktwniqqwsc.supabase.co:5432/postgres?sslmode=require"
export DB_AUTO_CREATE=true

echo "=== Local Database Test ==="
echo "DATABASE_URL: ${DATABASE_URL:0:60}..."
echo "DB_AUTO_CREATE: $DB_AUTO_CREATE"
echo ""

# Test Python connection first
echo "1. Testing Python database connection..."
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
"

if [ $? -ne 0 ]; then
    echo "Python connection test failed. Check DATABASE_URL."
    exit 1
fi

echo ""
echo "2. Starting FastAPI server..."
echo "   Server will run on http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""

# Start server
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
