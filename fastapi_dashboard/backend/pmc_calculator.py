"""
Performance Management Chart (PMC) calculator for TrainingPeaks-style analysis.

Calculates:
- TSS (Training Stress Score) per activity/day
- CTL (Chronic Training Load) - 42-day EMA
- ATL (Acute Training Load) - 7-day EMA  
- TSB (Training Stress Balance) = CTL - ATL
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from models import Activity, User
import math


def calculate_tss_for_activity(activity: Activity, sport_type: str) -> float:
    """
    Calculate TSS (Training Stress Score) for a single activity.
    
    Uses simple heuristic:
    - TSS = duration_hours * (IF^2) * 100
    - IF (Intensity Factor) based on HR if available, else default by sport
    
    Args:
        activity: Activity model instance
        sport_type: Sport type (Swim, Run, Ride, etc.)
        
    Returns:
        TSS value (float)
    """
    # Get duration in hours
    duration_s = activity.moving_time_s or activity.elapsed_time_s or 0
    duration_hours = duration_s / 3600.0
    
    if duration_hours == 0:
        return 0.0
    
    # Calculate Intensity Factor (IF)
    # If we have HR data, estimate IF from HR
    if activity.average_heartrate and activity.max_heartrate:
        # Simple heuristic: IF = (avg_hr / max_hr) * 0.9 + 0.1
        # This gives IF between 0.1 and 1.0
        hr_ratio = activity.average_heartrate / activity.max_heartrate
        if_estimate = (hr_ratio * 0.9) + 0.1
        # Clamp between 0.3 and 1.0
        if_estimate = max(0.3, min(1.0, if_estimate))
    else:
        # Default IF by sport type
        sport_lower = sport_type.lower()
        if 'swim' in sport_lower:
            if_estimate = 0.75
        elif 'run' in sport_lower:
            if_estimate = 0.78
        elif 'ride' in sport_lower or 'bike' in sport_lower or 'cycle' in sport_lower:
            if_estimate = 0.70
        else:
            # Default for unknown sports
            if_estimate = 0.75
    
    # TSS = duration_hours * (IF^2) * 100
    tss = duration_hours * (if_estimate ** 2) * 100
    
    return round(tss, 2)


def calculate_pmc(
    db: Session,
    user_id: int,
    days: int = 180,
    sport_filter: Optional[str] = None
) -> List[Dict]:
    """
    Calculate Performance Management Chart data (TSS, CTL, ATL, TSB) for a user.
    
    Args:
        db: Database session
        user_id: User ID
        days: Number of days to look back (default: 180)
        sport_filter: Filter by sport ('swim', 'run', 'ride', or None for all)
        
    Returns:
        List of daily PMC data points:
        [
            {"date": "YYYY-MM-DD", "tss": float, "ctl": float, "atl": float, "tsb": float},
            ...
        ]
    """
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Build query
    query = db.query(Activity).filter(
        and_(
            Activity.user_id == user_id,
            Activity.start_date >= start_date,
            Activity.start_date <= end_date
        )
    )
    
    # Apply sport filter if specified
    if sport_filter and sport_filter.lower() != 'all':
            sport_lower = sport_filter.lower()
            if sport_lower == 'swim':
                query = query.filter(
                    (func.lower(Activity.sport_type).in_(['swim', 'openwaterswim'])) |
                    (func.lower(Activity.type).in_(['swim']))
                )
            elif sport_lower == 'run':
                query = query.filter(
                    (func.lower(Activity.sport_type) == 'run') |
                    (func.lower(Activity.type) == 'run')
                )
            elif sport_lower in ['ride', 'bike']:
                query = query.filter(
                    (func.lower(Activity.sport_type).in_(['ride', 'virtualride'])) |
                    (func.lower(Activity.type).in_(['ride', 'bike', 'cycle']))
                )
    
    # Fetch activities
    activities = query.order_by(Activity.start_date).all()
    
    # Group activities by date and calculate daily TSS
    daily_tss = {}
    for activity in activities:
        if not activity.start_date:
            continue
        
        activity_date = activity.start_date.date()
        sport_type = activity.sport_type or activity.type or 'Unknown'
        
        tss = calculate_tss_for_activity(activity, sport_type)
        
        if activity_date in daily_tss:
            daily_tss[activity_date] += tss
        else:
            daily_tss[activity_date] = tss
    
    # Create date range with all days (fill missing with 0)
    all_dates = []
    current_date = start_date
    while current_date <= end_date:
        all_dates.append(current_date)
        current_date += timedelta(days=1)
    
    # Calculate CTL, ATL, TSB using EMA
    ctl = 0.0  # Chronic Training Load (42-day EMA)
    atl = 0.0  # Acute Training Load (7-day EMA)
    
    pmc_data = []
    
    for date in all_dates:
        tss = daily_tss.get(date, 0.0)
        
        # EMA update formulas
        # CTL: 42-day EMA
        if ctl == 0 and tss > 0:
            # Initialize on first day with activity
            ctl = tss
        elif ctl > 0:
            ctl = ctl + (tss - ctl) / 42.0
        
        # ATL: 7-day EMA
        if atl == 0 and tss > 0:
            # Initialize on first day with activity
            atl = tss
        elif atl > 0:
            atl = atl + (tss - atl) / 7.0
        
        # TSB = CTL - ATL
        tsb = ctl - atl
        
        pmc_data.append({
            "date": date.isoformat(),
            "tss": round(tss, 2),
            "ctl": round(ctl, 2),
            "atl": round(atl, 2),
            "tsb": round(tsb, 2)
        })
    
    return pmc_data
