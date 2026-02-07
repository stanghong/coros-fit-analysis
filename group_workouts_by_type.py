#!/usr/bin/env python3
"""
Group CSV workout files by activity type into separate folders.
"""

import os
import glob
import shutil
import pandas as pd
from pathlib import Path
from typing import Optional, Dict


def get_workout_type(csv_file_path: str) -> Optional[str]:
    """
    Determine the workout type from a CSV file.
    
    Args:
        csv_file_path: Path to the CSV file
        
    Returns:
        Workout type (running, swimming, walking, cycling) or None
    """
    try:
        # Read just the first row to get metadata
        df = pd.read_csv(csv_file_path, nrows=1)
        
        # Check session_sport column first (more reliable than activity_type codes)
        if 'session_sport' in df.columns:
            sport = df['session_sport'].iloc[0] if len(df) > 0 else None
            if pd.notna(sport):
                sport_str = str(sport).lower().strip()
                if sport_str in ['running', 'run']:
                    return 'running'
                elif sport_str in ['swimming', 'swim']:
                    return 'swimming'
                elif sport_str in ['walking', 'walk', 'hiking', 'hike']:
                    return 'walking'
                elif sport_str in ['cycling', 'bike', 'bicycle', 'cycle']:
                    return 'cycling'
        
        # Check activity_type column (may contain numeric codes or strings)
        if 'activity_type' in df.columns:
            activity_type = df['activity_type'].iloc[0] if len(df) > 0 else None
            if pd.notna(activity_type):
                # Handle string values
                if isinstance(activity_type, str):
                    activity_str = activity_type.lower().strip()
                    if activity_str in ['running', 'run']:
                        return 'running'
                    elif activity_str in ['swimming', 'swim']:
                        return 'swimming'
                    elif activity_str in ['walking', 'walk']:
                        return 'walking'
                    elif activity_str in ['cycling', 'bike', 'bicycle']:
                        return 'cycling'
                # Handle numeric codes (common FIT file sport codes)
                # Note: These codes may vary by device, but common ones are:
                # 0=generic, 1=running, 2=cycling, 5=swimming, etc.
                elif isinstance(activity_type, (int, float)):
                    # We'll skip numeric codes and rely on session_sport or other methods
                    pass
        
        # Check if we need to read more rows to find activity_type
        # Sometimes the first row might be empty
        df_full = pd.read_csv(csv_file_path, nrows=10)
        if 'activity_type' in df_full.columns:
            activity_type = df_full['activity_type'].dropna()
            if len(activity_type) > 0:
                activity_str = str(activity_type.iloc[0]).lower().strip()
                if activity_str in ['running', 'run']:
                    return 'running'
                elif activity_str in ['swimming', 'swim']:
                    return 'swimming'
                elif activity_str in ['walking', 'walk']:
                    return 'walking'
                elif activity_str in ['cycling', 'bike', 'bicycle']:
                    return 'cycling'
        
        # Try to infer from pace/speed if available
        # Running typically has pace < 10 min/km, walking > 12 min/km
        if 'speed' in df_full.columns or 'enhanced_speed' in df_full.columns:
            speed_col = 'enhanced_speed' if 'enhanced_speed' in df_full.columns else 'speed'
            speeds = df_full[speed_col].dropna()
            if len(speeds) > 0:
                avg_speed = speeds.mean()  # m/s
                if avg_speed > 0:
                    pace_min_per_km = (1000.0 / avg_speed) / 60.0  # minutes per km
                    if pace_min_per_km < 8.0:
                        return 'running'
                    elif pace_min_per_km > 12.0:
                        return 'walking'
        
        return None
        
    except Exception as e:
        print(f"⚠ Error reading {os.path.basename(csv_file_path)}: {e}")
        return None


def group_csv_files(csv_folder: str) -> Dict[str, int]:
    """
    Group CSV files by workout type into separate folders.
    
    Args:
        csv_folder: Directory containing CSV files
        
    Returns:
        Dictionary with statistics about the grouping
    """
    # Create output folders
    folders = {
        'running': os.path.join(csv_folder, 'running'),
        'swimming': os.path.join(csv_folder, 'swimming'),
        'walking': os.path.join(csv_folder, 'walking'),
        'cycling': os.path.join(csv_folder, 'cycling')
    }
    
    for folder_path in folders.values():
        os.makedirs(folder_path, exist_ok=True)
    
    # Find all CSV files (excluding summary file)
    csv_files = [f for f in glob.glob(os.path.join(csv_folder, "*.csv")) 
                 if not os.path.basename(f).startswith('_')]
    
    print(f"Found {len(csv_files)} CSV files to organize")
    print("=" * 80)
    
    stats = {
        'running': 0,
        'swimming': 0,
        'walking': 0,
        'cycling': 0,
        'unknown': 0,
        'errors': 0
    }
    
    # Process each file
    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        workout_type = get_workout_type(csv_file)
        
        if workout_type and workout_type in folders:
            # Move file to appropriate folder
            dest_path = os.path.join(folders[workout_type], filename)
            shutil.move(csv_file, dest_path)
            stats[workout_type] += 1
            print(f"✓ {filename} -> {workout_type}/")
        elif workout_type is None:
            stats['unknown'] += 1
            print(f"⚠ {filename} -> Unknown workout type (keeping in root)")
        else:
            stats['errors'] += 1
            print(f"✗ {filename} -> Error determining type")
    
    return stats


def move_summary_file(csv_folder: str) -> None:
    """Move the summary file to the root if it exists."""
    summary_file = os.path.join(csv_folder, '_summary.csv')
    if os.path.exists(summary_file):
        print(f"\n✓ Summary file kept in root: _summary.csv")


if __name__ == "__main__":
    csv_folder_path = "/Users/hongtang/Documents/coros_fit/csv_folder"
    
    print("📁 Organizing CSV files by workout type")
    print("=" * 80)
    
    stats = group_csv_files(csv_folder_path)
    
    move_summary_file(csv_folder_path)
    
    print("\n" + "=" * 80)
    print("📊 Organization Statistics:")
    print(f"  Running: {stats['running']} files")
    print(f"  Swimming: {stats['swimming']} files")
    print(f"  Walking: {stats['walking']} files")
    print(f"  Cycling: {stats['cycling']} files")
    print(f"  Unknown: {stats['unknown']} files")
    print(f"  Errors: {stats['errors']} files")
    
    print("\n✅ Organization complete!")
    print(f"📁 Files organized in: {csv_folder_path}")
