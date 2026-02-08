"""
Background sync job for Strava activities.

This module provides a background task that periodically syncs activities
for all connected users.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session

from db import get_db, engine
from models import User, StravaToken
from strava_sync import sync_activities
from strava_rate_limiter import get_rate_limit_status

logger = logging.getLogger(__name__)

# Sync configuration
SYNC_INTERVAL_MINUTES = 60  # Sync every hour
SYNC_BATCH_SIZE = 5  # Number of users to sync per batch
SYNC_DELAY_BETWEEN_USERS = 10  # Seconds to wait between users (to respect rate limits)


class BackgroundSyncJob:
    """Background job for syncing Strava activities."""
    
    def __init__(self):
        self.running = False
        self.task = None
    
    async def sync_user(self, user: User, db: Session) -> dict:
        """
        Sync activities for a single user.
        
        Returns:
            Sync result dict or None if failed
        """
        try:
            result = await sync_activities(
                db=db,
                athlete_id=user.strava_athlete_id,
                limit=30,
                incremental=True,
                max_pages=3  # Limit pages for background sync
            )
            logger.info(
                f"Background sync for user {user.id} (athlete_id={user.strava_athlete_id}): "
                f"{result['new_count']} new, {result['updated_count']} updated"
            )
            return result
        except Exception as e:
            logger.error(f"Background sync failed for user {user.id}: {str(e)}")
            return None
    
    async def sync_all_users(self):
        """Sync activities for all users with valid tokens."""
        if not engine:
            logger.warning("Database not available, skipping background sync")
            return
        
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Get all users with valid tokens
            users_with_tokens = db.query(User).join(StravaToken).all()
            
            if not users_with_tokens:
                logger.info("No users with Strava tokens found, skipping sync")
                return
            
            logger.info(f"Starting background sync for {len(users_with_tokens)} users")
            
            # Check rate limit status
            rate_limit_status = get_rate_limit_status()
            if rate_limit_status["remaining_15min"] < SYNC_BATCH_SIZE:
                logger.warning(
                    f"Rate limit low ({rate_limit_status['remaining_15min']} remaining), "
                    f"skipping background sync"
                )
                return
            
            # Sync users in batches
            for i, user in enumerate(users_with_tokens):
                if not self.running:
                    logger.info("Background sync stopped")
                    break
                
                # Check rate limit before each user
                rate_limit_status = get_rate_limit_status()
                if rate_limit_status["remaining_15min"] < 5:
                    logger.warning("Rate limit too low, pausing sync")
                    await asyncio.sleep(60)  # Wait 1 minute
                    continue
                
                # Sync this user
                await self.sync_user(user, db)
                
                # Wait between users to respect rate limits
                if i < len(users_with_tokens) - 1:
                    await asyncio.sleep(SYNC_DELAY_BETWEEN_USERS)
            
            logger.info("Background sync completed")
            
        except Exception as e:
            logger.error(f"Error in background sync: {str(e)}")
        finally:
            db.close()
    
    async def run_loop(self):
        """Main loop for background sync."""
        logger.info(f"Background sync job started (interval: {SYNC_INTERVAL_MINUTES} minutes)")
        
        while self.running:
            try:
                await self.sync_all_users()
            except Exception as e:
                logger.error(f"Error in background sync loop: {str(e)}")
            
            # Wait for next sync interval
            if self.running:
                await asyncio.sleep(SYNC_INTERVAL_MINUTES * 60)
    
    def start(self):
        """Start the background sync job."""
        if self.running:
            logger.warning("Background sync job already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self.run_loop())
        logger.info("Background sync job started")
    
    def stop(self):
        """Stop the background sync job."""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("Background sync job stopped")


# Global background sync job instance
_background_sync_job: BackgroundSyncJob = None


def get_background_sync_job() -> BackgroundSyncJob:
    """Get or create the global background sync job instance."""
    global _background_sync_job
    if _background_sync_job is None:
        _background_sync_job = BackgroundSyncJob()
    return _background_sync_job


def start_background_sync():
    """Start the background sync job."""
    job = get_background_sync_job()
    job.start()


def stop_background_sync():
    """Stop the background sync job."""
    job = get_background_sync_job()
    job.stop()
