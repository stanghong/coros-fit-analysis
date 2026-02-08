"""
Development-only routes for testing database operations.

These routes are only enabled when ENV=dev to prevent abuse in production.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import os
import time
from typing import Dict

# Import database dependencies
try:
    from db import get_db
    from models import User, StravaToken
    from strava_store import get_or_create_user, upsert_strava_token
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

router = APIRouter(prefix="/dev", tags=["dev"])


def check_dev_env():
    """
    Check if we're in development environment.
    Raises 404 if not in dev mode.
    """
    env = os.getenv("ENV", "").lower()
    if env != "dev":
        raise HTTPException(status_code=404, detail="Not Found")


@router.post("/seed-user")
async def seed_test_user(db: Session = Depends(get_db)) -> Dict:
    """
    Dev-only endpoint to create a test user and token for database testing.
    
    Only available when ENV=dev.
    
    Creates:
    - User with strava_athlete_id=123456789
    - Token row with dummy test values
    
    Returns:
        {
            "user_id": int,
            "strava_athlete_id": int,
            "message": "Test user and token created"
        }
    """
    # Check if we're in dev mode
    check_dev_env()
    
    if not DB_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available"
        )
    
    try:
        # Create or get user with strava_athlete_id=123456789
        athlete_id = 123456789
        user = get_or_create_user(db, athlete_id)
        
        # Calculate expires_at (now + 1 day)
        expires_at = int(time.time()) + (24 * 60 * 60)  # 1 day in seconds
        
        # Prepare token payload with dummy values
        token_payload = {
            "access_token": "test_access",
            "refresh_token": "test_refresh",
            "expires_at": expires_at,
            "scope": "read,activity:read_all"
        }
        
        # Upsert token
        token = upsert_strava_token(db, user.id, token_payload)
        
        return {
            "user_id": user.id,
            "strava_athlete_id": user.strava_athlete_id,
            "message": "Test user and token created",
            "token_expires_at": expires_at
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error seeding test user: {str(e)}"
        )
