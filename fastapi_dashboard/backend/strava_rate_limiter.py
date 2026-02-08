"""
Rate limiter for Strava API calls.

Strava API limits:
- 200 requests per 15 minutes
- 2000 requests per day

This module tracks API calls and enforces rate limits.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
import time
import os

# Rate limit configuration
RATE_LIMIT_15MIN = 200  # Requests per 15 minutes
RATE_LIMIT_DAY = 2000   # Requests per day
WINDOW_15MIN = 15 * 60  # 15 minutes in seconds
WINDOW_DAY = 24 * 60 * 60  # 24 hours in seconds

# In-memory rate limit tracking (in production, use Redis or database)
_rate_limit_15min: deque = deque()  # Timestamps of requests in last 15 minutes
_rate_limit_day: deque = deque()    # Timestamps of requests in last 24 hours


def _clean_old_requests():
    """Remove requests outside the time windows."""
    current_time = time.time()
    
    # Clean 15-minute window
    while _rate_limit_15min and _rate_limit_15min[0] < current_time - WINDOW_15MIN:
        _rate_limit_15min.popleft()
    
    # Clean 24-hour window
    while _rate_limit_day and _rate_limit_day[0] < current_time - WINDOW_DAY:
        _rate_limit_day.popleft()


def check_rate_limit() -> tuple[bool, Optional[str]]:
    """
    Check if we can make an API request without exceeding rate limits.
    
    Returns:
        (can_proceed: bool, error_message: Optional[str])
    """
    _clean_old_requests()
    
    current_time = time.time()
    
    # Check 15-minute limit
    if len(_rate_limit_15min) >= RATE_LIMIT_15MIN:
        oldest_request = _rate_limit_15min[0]
        wait_time = (oldest_request + WINDOW_15MIN) - current_time
        if wait_time > 0:
            return False, f"Rate limit exceeded: 200 requests per 15 minutes. Wait {int(wait_time)} seconds."
    
    # Check daily limit
    if len(_rate_limit_day) >= RATE_LIMIT_DAY:
        oldest_request = _rate_limit_day[0]
        wait_time = (oldest_request + WINDOW_DAY) - current_time
        if wait_time > 0:
            return False, f"Rate limit exceeded: 2000 requests per day. Wait {int(wait_time / 3600)} hours."
    
    return True, None


def record_api_call():
    """Record that an API call was made."""
    current_time = time.time()
    _rate_limit_15min.append(current_time)
    _rate_limit_day.append(current_time)


def get_rate_limit_status() -> Dict:
    """
    Get current rate limit status.
    
    Returns:
        {
            "requests_15min": int,
            "requests_day": int,
            "remaining_15min": int,
            "remaining_day": int,
            "reset_15min_seconds": int,
            "reset_day_seconds": int
        }
    """
    _clean_old_requests()
    
    current_time = time.time()
    
    requests_15min = len(_rate_limit_15min)
    requests_day = len(_rate_limit_day)
    
    # Calculate reset times
    reset_15min = 0
    if _rate_limit_15min:
        oldest_15min = _rate_limit_15min[0]
        reset_15min = max(0, int((oldest_15min + WINDOW_15MIN) - current_time))
    
    reset_day = 0
    if _rate_limit_day:
        oldest_day = _rate_limit_day[0]
        reset_day = max(0, int((oldest_day + WINDOW_DAY) - current_time))
    
    return {
        "requests_15min": requests_15min,
        "requests_day": requests_day,
        "remaining_15min": max(0, RATE_LIMIT_15MIN - requests_15min),
        "remaining_day": max(0, RATE_LIMIT_DAY - requests_day),
        "reset_15min_seconds": reset_15min,
        "reset_day_seconds": reset_day
    }
