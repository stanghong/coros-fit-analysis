"""
Database storage functions for Strava OAuth tokens and user management.

This module provides functions to persist Strava OAuth tokens in the database
and manage user records linked to Strava athlete IDs.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict, List
from datetime import datetime
import os
import time
import httpx
from models import User, StravaToken, Activity

# Strava OAuth configuration (for token refresh)
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID", "")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "")


def get_or_create_user(db: Session, athlete_id: int, athlete_info: Optional[Dict] = None) -> User:
    """
    Get or create a user for the given Strava athlete ID.
    Optionally update athlete info (username, firstname, lastname).
    
    Args:
        db: SQLAlchemy database session
        athlete_id: Strava athlete ID
        athlete_info: Optional dict with 'username', 'firstname', 'lastname' keys
        
    Returns:
        User object (existing or newly created)
    """
    # Try to find existing user by Strava athlete ID
    user = db.query(User).filter(User.strava_athlete_id == athlete_id).first()
    
    if user:
        # Update athlete info if provided
        if athlete_info:
            if 'username' in athlete_info:
                user.strava_username = athlete_info.get('username')
            if 'firstname' in athlete_info:
                user.strava_firstname = athlete_info.get('firstname')
            if 'lastname' in athlete_info:
                user.strava_lastname = athlete_info.get('lastname')
            try:
                db.commit()
                db.refresh(user)
            except Exception as e:
                print(f"WARNING: Failed to update athlete info: {e}")
        return user
    
    # Create new user if not found
    user = User(
        strava_athlete_id=athlete_id,
        strava_username=athlete_info.get('username') if athlete_info else None,
        strava_firstname=athlete_info.get('firstname') if athlete_info else None,
        strava_lastname=athlete_info.get('lastname') if athlete_info else None
    )
    db.add(user)
    
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        # Race condition: another request created the user between query and insert
        db.rollback()
        # Try to fetch again
        user = db.query(User).filter(User.strava_athlete_id == athlete_id).first()
        if user:
            # Update athlete info if provided
            if athlete_info:
                if 'username' in athlete_info:
                    user.strava_username = athlete_info.get('username')
                if 'firstname' in athlete_info:
                    user.strava_firstname = athlete_info.get('firstname')
                if 'lastname' in athlete_info:
                    user.strava_lastname = athlete_info.get('lastname')
                try:
                    db.commit()
                    db.refresh(user)
                except Exception as e:
                    print(f"WARNING: Failed to update athlete info: {e}")
            return user
        raise


def upsert_strava_token(db: Session, user_id: int, token_payload: Dict) -> StravaToken:
    """
    Insert or update Strava OAuth tokens for a user.
    
    Args:
        db: SQLAlchemy database session
        user_id: User ID (from User model)
        token_payload: Dictionary containing:
            - access_token: str
            - refresh_token: str
            - expires_at: int (Unix timestamp)
            - scope: str (optional)
            
    Returns:
        StravaToken object (inserted or updated)
    """
    # Extract token data
    access_token = token_payload.get("access_token")
    refresh_token = token_payload.get("refresh_token")
    expires_at = token_payload.get("expires_at")
    scope = token_payload.get("scope")
    
    if not access_token or not refresh_token or expires_at is None:
        raise ValueError("Missing required token fields: access_token, refresh_token, expires_at")
    
    # Try to find existing token record
    token = db.query(StravaToken).filter(StravaToken.user_id == user_id).first()
    
    if token:
        # Update existing token
        token.access_token = access_token
        token.refresh_token = refresh_token
        token.expires_at = expires_at
        if scope is not None:
            token.scope = scope
        # updated_at is automatically set by onupdate
    else:
        # Create new token record
        token = StravaToken(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scope=scope
        )
        db.add(token)
    
    try:
        db.commit()
        db.refresh(token)
        return token
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Failed to save token: {str(e)}")


def get_token_for_athlete(db: Session, athlete_id: int) -> Optional[StravaToken]:
    """
    Get Strava token for a given athlete ID.
    
    Args:
        db: SQLAlchemy database session
        athlete_id: Strava athlete ID
        
    Returns:
        StravaToken object if found, None otherwise
    """
    user = db.query(User).filter(User.strava_athlete_id == athlete_id).first()
    
    if not user:
        return None
    
    token = db.query(StravaToken).filter(StravaToken.user_id == user.id).first()
    return token


async def ensure_valid_access_token(db: Session, athlete_id: int) -> Optional[str]:
    """
    Ensure we have a valid access token for the given athlete.
    If token is expired (with 60s buffer), refresh it using the refresh token.
    
    Args:
        db: SQLAlchemy database session
        athlete_id: Strava athlete ID
        
    Returns:
        Valid access_token string, or None if token not found or refresh failed
    """
    # Get token from database
    token = get_token_for_athlete(db, athlete_id)
    
    if not token:
        return None
    
    # Check if token is expired (with 60 second buffer)
    current_time = int(time.time())
    expires_at = token.expires_at
    buffer_seconds = 60
    
    # If token expires within the next 60 seconds, refresh it
    if expires_at <= (current_time + buffer_seconds):
        # Token is expired or about to expire, refresh it
        if not STRAVA_CLIENT_ID or not STRAVA_CLIENT_SECRET:
            print("WARNING: Strava client credentials not configured. Cannot refresh token.")
            return None
        
        if not token.refresh_token:
            print("WARNING: No refresh token available. Cannot refresh access token.")
            return None
        
        try:
            # Call Strava token refresh endpoint
            async with httpx.AsyncClient() as client:
                refresh_response = await client.post(
                    "https://www.strava.com/oauth/token",
                    data={
                        "client_id": STRAVA_CLIENT_ID,
                        "client_secret": STRAVA_CLIENT_SECRET,
                        "grant_type": "refresh_token",
                        "refresh_token": token.refresh_token
                    },
                    timeout=10.0
                )
                
                if refresh_response.status_code != 200:
                    error_detail = refresh_response.text
                    try:
                        error_json = refresh_response.json()
                        error_detail = str(error_json)
                    except:
                        pass
                    print(f"ERROR: Strava token refresh failed (status {refresh_response.status_code}): {error_detail}")
                    print(f"DEBUG: Client ID: {STRAVA_CLIENT_ID[:10]}... (first 10 chars)")
                    print(f"DEBUG: Has refresh_token: {bool(token.refresh_token)}")
                    print(f"DEBUG: Refresh token length: {len(token.refresh_token) if token.refresh_token else 0}")
                    return None
                
                refresh_data = refresh_response.json()
                
                # Update token in database with new values
                token.access_token = refresh_data.get("access_token")
                token.refresh_token = refresh_data.get("refresh_token", token.refresh_token)  # Strava may rotate refresh token
                token.expires_at = refresh_data.get("expires_at")
                if refresh_data.get("scope"):
                    token.scope = refresh_data.get("scope")
                
                try:
                    db.commit()
                    db.refresh(token)
                    print(f"INFO: Token refreshed successfully for athlete_id={athlete_id}")
                except Exception as e:
                    db.rollback()
                    print(f"ERROR: Failed to save refreshed token to database: {str(e)}")
                    return None
        
        except httpx.HTTPStatusError as e:
            print(f"ERROR: HTTP error during token refresh: {e.response.text}")
            return None
        except Exception as e:
            print(f"ERROR: Exception during token refresh: {str(e)}")
            return None
    
    # Return the (now valid) access token
    return token.access_token


def upsert_activity(db: Session, user_id: int, activity_data: Dict) -> Activity:
    """
    Insert or update an activity in the database.
    
    Args:
        db: SQLAlchemy database session
        user_id: User ID (from User model)
        activity_data: Dictionary containing Strava activity data:
            - id: int (Strava activity ID, required)
            - type: str (sport_type)
            - start_date: str (ISO format datetime)
            - distance: float (meters)
            - moving_time: int (seconds)
            - elapsed_time: int (seconds)
            - average_heartrate: float (optional)
            - max_heartrate: float (optional)
            - total_elevation_gain: float (optional)
            - raw_json: dict (full Strava API response)
            
    Returns:
        Activity object (inserted or updated)
    """
    activity_id = activity_data.get("id")
    if not activity_id:
        raise ValueError("Activity ID is required")
    
    # Parse start_date if provided
    start_date = None
    if activity_data.get("start_date"):
        try:
            # Strava returns ISO format: "2024-01-15T10:30:00Z"
            start_date_str = activity_data.get("start_date")
            if isinstance(start_date_str, str):
                # Replace Z with +00:00 for ISO format parsing
                if start_date_str.endswith("Z"):
                    start_date_str = start_date_str[:-1] + "+00:00"
                start_date = datetime.fromisoformat(start_date_str)
        except Exception as e:
            print(f"WARNING: Failed to parse start_date '{activity_data.get('start_date')}': {e}")
    
    # Try to find existing activity
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    
    if activity:
        # Update existing activity
        activity.type = activity_data.get("sport_type") or activity_data.get("type")
        activity.start_date = start_date or activity.start_date
        activity.distance_m = activity_data.get("distance")
        activity.moving_time_s = activity_data.get("moving_time")
        activity.elapsed_time_s = activity_data.get("elapsed_time")
        activity.average_heartrate = activity_data.get("average_heartrate")
        activity.max_heartrate = activity_data.get("max_heartrate")
        activity.total_elevation_gain = activity_data.get("total_elevation_gain")
        if activity_data.get("raw_json"):
            activity.raw_json = activity_data.get("raw_json")
    else:
        # Create new activity
        activity = Activity(
            id=activity_id,
            user_id=user_id,
            type=activity_data.get("sport_type") or activity_data.get("type"),
            start_date=start_date,
            distance_m=activity_data.get("distance"),
            moving_time_s=activity_data.get("moving_time"),
            elapsed_time_s=activity_data.get("elapsed_time"),
            average_heartrate=activity_data.get("average_heartrate"),
            max_heartrate=activity_data.get("max_heartrate"),
            total_elevation_gain=activity_data.get("total_elevation_gain"),
            raw_json=activity_data.get("raw_json")
        )
        db.add(activity)
    
    try:
        db.commit()
        db.refresh(activity)
        return activity
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Failed to save activity: {str(e)}")
