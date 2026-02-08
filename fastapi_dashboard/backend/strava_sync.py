"""
Strava sync service with incremental sync, retry logic, and rate limiting.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc
import httpx
import asyncio
import logging

from models import User, Activity
from strava_store import ensure_valid_access_token, upsert_activity, get_token_for_athlete
from strava_rate_limiter import check_rate_limit, record_api_call, get_rate_limit_status
from strava_retry import retry_with_backoff

logger = logging.getLogger(__name__)

# Track last sync time per user (in production, store in database)
_last_sync_times: Dict[int, datetime] = {}


def get_last_sync_time(db: Session, user_id: int) -> Optional[datetime]:
    """
    Get the timestamp of the most recent activity for a user (last sync time).
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Datetime of most recent activity, or None if no activities
    """
    last_activity = db.query(Activity).filter(
        Activity.user_id == user_id
    ).order_by(desc(Activity.start_date)).first()
    
    if last_activity and last_activity.start_date:
        return last_activity.start_date
    return None


async def sync_activities(
    db: Session,
    athlete_id: int,
    limit: int = 30,
    incremental: bool = True,
    max_pages: int = 10
) -> Dict:
    """
    Sync activities from Strava with incremental sync, retry logic, and rate limiting.
    
    Args:
        db: Database session
        athlete_id: Strava athlete ID
        limit: Number of activities per page
        incremental: If True, only fetch activities newer than last sync
        max_pages: Maximum number of pages to fetch
        
    Returns:
        {
            "synced_count": int,
            "new_count": int,
            "updated_count": int,
            "pages_fetched": int,
            "rate_limit_status": dict
        }
    """
    # Get user
    user = db.query(User).filter(User.strava_athlete_id == athlete_id).first()
    if not user:
        raise ValueError(f"User not found for athlete_id={athlete_id}")
    
    # Get valid access token
    access_token = await ensure_valid_access_token(db, athlete_id)
    if not access_token:
        raise ValueError("No valid access token found")
    
    # Get last sync time if incremental
    last_sync_time = None
    if incremental:
        last_sync_time = get_last_sync_time(db, user.id)
        if last_sync_time:
            logger.info(f"Incremental sync: last activity was at {last_sync_time}")
    
    # Check rate limit before starting
    can_proceed, error_msg = check_rate_limit()
    if not can_proceed:
        raise ValueError(f"Rate limit exceeded: {error_msg}")
    
    synced_count = 0
    new_count = 0
    updated_count = 0
    pages_fetched = 0
    
    async with httpx.AsyncClient() as client:
        page = 1
        
        while page <= max_pages:
            # Check rate limit before each page
            can_proceed, error_msg = check_rate_limit()
            if not can_proceed:
                logger.warning(f"Rate limit reached after {pages_fetched} pages: {error_msg}")
                break
            
            # Fetch activities with retry logic
            async def fetch_page():
                record_api_call()  # Record before making call
                return await client.get(
                    "https://www.strava.com/api/v3/athlete/activities",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"per_page": limit, "page": page},
                    timeout=30.0
                )
            
            try:
                response = await retry_with_backoff(
                    fetch_page,
                    description=f"Fetching Strava activities page {page}"
                )
                response.raise_for_status()
                activities = response.json()
                
                if not activities:
                    # No more activities
                    break
                
                # Process activities
                page_new = 0
                page_updated = 0
                
                for activity_data in activities:
                    # If incremental and we've reached activities older than last sync, stop
                    if incremental and last_sync_time:
                        activity_start = activity_data.get("start_date")
                        if activity_start:
                            try:
                                activity_dt = datetime.fromisoformat(activity_start.replace('Z', '+00:00'))
                                if activity_dt <= last_sync_time:
                                    logger.info(f"Reached activities older than last sync, stopping at page {page}")
                                    return {
                                        "synced_count": synced_count,
                                        "new_count": new_count,
                                        "updated_count": updated_count,
                                        "pages_fetched": pages_fetched,
                                        "rate_limit_status": get_rate_limit_status()
                                    }
                            except Exception as e:
                                logger.warning(f"Failed to parse activity date: {e}")
                    
                    # Prepare activity payload
                    activity_payload = {
                        "id": activity_data.get("id"),
                        "sport_type": activity_data.get("sport_type"),
                        "type": activity_data.get("type"),
                        "start_date": activity_data.get("start_date"),
                        "distance": activity_data.get("distance"),
                        "moving_time": activity_data.get("moving_time"),
                        "elapsed_time": activity_data.get("elapsed_time"),
                        "average_heartrate": activity_data.get("average_heartrate"),
                        "max_heartrate": activity_data.get("max_heartrate"),
                        "total_elevation_gain": activity_data.get("total_elevation_gain"),
                        "raw_json": activity_data
                    }
                    
                    # Check if activity already exists
                    existing = db.query(Activity).filter(Activity.id == activity_data.get("id")).first()
                    is_new = existing is None
                    
                    # Upsert activity with error handling
                    try:
                        upsert_activity(db, user.id, activity_payload)
                        db.commit()  # Commit after each activity
                        
                        if is_new:
                            page_new += 1
                        else:
                            page_updated += 1
                    except Exception as e:
                        db.rollback()
                        logger.warning(f"Failed to upsert activity {activity_data.get('id')}: {e}")
                        continue
                
                synced_count += len(activities)
                new_count += page_new
                updated_count += page_updated
                pages_fetched += 1
                
                logger.info(f"Page {page}: synced {len(activities)} activities ({page_new} new, {page_updated} updated)")
                
                # If we got fewer activities than requested, we're done
                if len(activities) < limit:
                    break
                
                page += 1
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise ValueError("Strava access token expired or invalid")
                elif e.response.status_code == 429:
                    # Rate limit hit during request
                    rate_limit_status = get_rate_limit_status()
                    raise ValueError(f"Rate limit exceeded: {rate_limit_status}")
                else:
                    raise
    
    return {
        "synced_count": synced_count,
        "new_count": new_count,
        "updated_count": updated_count,
        "pages_fetched": pages_fetched,
        "rate_limit_status": get_rate_limit_status()
    }
