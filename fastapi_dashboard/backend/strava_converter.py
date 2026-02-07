"""
Convert Strava activity data to format compatible with workout analysis.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional


def strava_streams_to_dataframe(activity: Dict, streams: Dict) -> pd.DataFrame:
    """
    Convert Strava activity and streams data to DataFrame format expected by analysis engine.
    
    Args:
        activity: Strava activity summary (from /athlete/activities)
        streams: Strava activity streams dict (keyed by stream type)
    
    Returns:
        DataFrame in the format expected by analysis_engine
    """
    # Extract time-series data from streams
    # streams is a dict where keys are stream types (e.g., 'time', 'distance')
    # and values are dicts with 'data' and 'series_type' keys
    time_data = streams.get('time', {}).get('data', []) if isinstance(streams.get('time'), dict) else []
    distance_data = streams.get('distance', {}).get('data', []) if isinstance(streams.get('distance'), dict) else []
    velocity_smooth = streams.get('velocity_smooth', {}).get('data', []) if isinstance(streams.get('velocity_smooth'), dict) else []
    cadence_data = streams.get('cadence', {}).get('data', []) if isinstance(streams.get('cadence'), dict) else []
    heartrate_data = streams.get('heartrate', {}).get('data', []) if isinstance(streams.get('heartrate'), dict) else []
    
    # Create DataFrame with time-series data
    data = {
        'time': time_data,
        'distance': distance_data,
        'speed': velocity_smooth,
        'cadence': cadence_data,
        'heart_rate': heartrate_data
    }
    
    # Find minimum length to avoid index errors
    min_length = min([len(v) for v in data.values() if len(v) > 0] or [0])
    
    if min_length == 0:
        # If no stream data, create minimal DataFrame from activity summary
        return create_minimal_dataframe_from_activity(activity)
    
    # Trim all arrays to same length
    for key in data:
        if len(data[key]) > 0:
            data[key] = data[key][:min_length]
        else:
            data[key] = [None] * min_length
    
    df = pd.DataFrame(data)
    
    # Add session metadata columns (analysis engine expects these in first row)
    # These will be duplicated for all rows, but analysis engine uses .iloc[0]
    df['session_start_time'] = activity.get('start_date', datetime.now().isoformat())
    df['session_total_distance'] = activity.get('distance', 0)  # meters
    df['session_total_elapsed_time'] = activity.get('elapsed_time', 0)  # seconds
    df['session_avg_speed'] = activity.get('average_speed', 0)  # m/s
    df['session_avg_cadence'] = activity.get('average_cadence', 0)  # strokes/min for swimming
    df['session_pool_length'] = 0  # Not available from Strava, set to 0
    
    # Map Strava fields to expected column names
    # Analysis engine prefers 'enhanced_speed' over 'speed'
    if 'speed' in df.columns:
        df['enhanced_speed'] = df['speed']
    
    # Filter out invalid data
    if 'speed' in df.columns:
        df = df[df['speed'] > 0]  # Remove stops/zeros
    
    return df


def create_minimal_dataframe_from_activity(activity: Dict) -> pd.DataFrame:
    """
    Create a minimal DataFrame from activity summary when streams are not available.
    This provides basic analysis but limited metrics.
    """
    # Create a single-row DataFrame with session data
    data = {
        'time': [0],
        'distance': [activity.get('distance', 0)],
        'speed': [activity.get('average_speed', 0)],
        'cadence': [activity.get('average_cadence', 0)],
        'heart_rate': [activity.get('average_heartrate', 0)],
        'session_start_time': [activity.get('start_date', datetime.now().isoformat())],
        'session_total_distance': [activity.get('distance', 0)],
        'session_total_elapsed_time': [activity.get('elapsed_time', 0)],
        'session_avg_speed': [activity.get('average_speed', 0)],
        'session_avg_cadence': [activity.get('average_cadence', 0)],
        'session_pool_length': [0],
        'enhanced_speed': [activity.get('average_speed', 0)]
    }
    
    return pd.DataFrame(data)


def is_swimming_activity(activity: Dict) -> bool:
    """Check if activity is a swimming workout."""
    sport_type = activity.get('sport_type', '').lower()
    return sport_type == 'swim' or 'swim' in sport_type
