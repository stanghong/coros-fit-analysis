#!/usr/bin/env python3
"""
Analyze long runs and generate quality scores (A, B, or C).
"""

import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional


def get_long_runs(running_folder: str, min_distance_km: float = 10.0, top_n: int = 5) -> List[Dict]:
    """
    Get the most recent long runs from the running folder.
    
    Args:
        running_folder: Path to running folder
        min_distance_km: Minimum distance to qualify as "long run"
        top_n: Number of runs to return
        
    Returns:
        List of dictionaries with run information
    """
    csv_files = glob.glob(os.path.join(running_folder, "*.csv"))
    
    runs = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, nrows=1)
            
            # Get distance from session data
            distance = None
            if 'session_total_distance' in df.columns:
                distance = df['session_total_distance'].iloc[0]
            elif 'total_distance' in df.columns:
                distance = df['total_distance'].iloc[0]
            
            # Convert distance from meters to km if needed
            if distance is not None:
                if pd.notna(distance):
                    # If distance is > 100, assume it's in meters
                    if distance > 100:
                        distance = distance / 1000.0
                    # If distance is very small (< 0.1 km), it's likely already in km but too short
                    elif distance < 0.1:
                        distance = None  # Skip very short activities
            
            # Get timestamp
            timestamp = None
            if 'session_start_time' in df.columns:
                timestamp = df['session_start_time'].iloc[0]
            elif 'timestamp' in df.columns:
                timestamp = df['timestamp'].iloc[0]
            
            if distance is not None and distance >= min_distance_km:
                runs.append({
                    'file': csv_file,
                    'distance_km': distance,
                    'timestamp': timestamp,
                    'filename': os.path.basename(csv_file)
                })
        except Exception as e:
            continue
    
    # Sort by timestamp (most recent first)
    runs.sort(key=lambda x: x['timestamp'] if x['timestamp'] else '', reverse=True)
    
    return runs[:top_n]


def calculate_hr_stability(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate heart rate stability metrics.
    
    Returns:
        Dictionary with HR stability metrics
    """
    if 'heart_rate' not in df.columns:
        return {'stability_score': 0, 'cv': 100, 'drift': 0}
    
    hr_data = df['heart_rate'].dropna()
    
    if len(hr_data) < 10:
        return {'stability_score': 0, 'cv': 100, 'drift': 0}
    
    # Calculate coefficient of variation (lower is better)
    cv = (hr_data.std() / hr_data.mean() * 100) if hr_data.mean() > 0 else 100
    
    # Calculate HR drift (increase over time)
    # Split into first and second half
    mid_point = len(hr_data) // 2
    first_half_avg = hr_data.iloc[:mid_point].mean()
    second_half_avg = hr_data.iloc[mid_point:].mean()
    drift = second_half_avg - first_half_avg
    
    # Stability score: 0-100 (higher is better)
    # Good stability: CV < 5%, drift < 5 bpm
    stability_score = max(0, 100 - (cv * 10) - abs(drift) * 2)
    
    return {
        'stability_score': stability_score,
        'cv': cv,
        'drift': drift,
        'avg_hr': hr_data.mean(),
        'min_hr': hr_data.min(),
        'max_hr': hr_data.max()
    }


def calculate_cadence_stability(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate cadence stability metrics.
    
    Returns:
        Dictionary with cadence stability metrics
    """
    cadence_col = None
    for col in ['cadence', 'running_cadence', 'session_avg_running_cadence']:
        if col in df.columns:
            cadence_col = col
            break
    
    if not cadence_col:
        return {'stability_score': 0, 'cv': 100, 'degradation': 0}
    
    cadence_data = df[cadence_col].dropna()
    
    if len(cadence_data) < 10:
        return {'stability_score': 0, 'cv': 100, 'degradation': 0}
    
    # Calculate coefficient of variation
    cv = (cadence_data.std() / cadence_data.mean() * 100) if cadence_data.mean() > 0 else 100
    
    # Calculate cadence degradation (decrease over time)
    mid_point = len(cadence_data) // 2
    first_half_avg = cadence_data.iloc[:mid_point].mean()
    second_half_avg = cadence_data.iloc[mid_point:].mean()
    degradation = first_half_avg - second_half_avg  # Positive = degradation
    
    # Stability score: 0-100 (higher is better)
    # Good stability: CV < 3%, degradation < 2 spm
    stability_score = max(0, 100 - (cv * 15) - abs(degradation) * 5)
    
    return {
        'stability_score': stability_score,
        'cv': cv,
        'degradation': degradation,
        'avg_cadence': cadence_data.mean(),
        'min_cadence': cadence_data.min(),
        'max_cadence': cadence_data.max()
    }


def calculate_pace_stability(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate pace stability and degradation metrics.
    
    Returns:
        Dictionary with pace stability metrics
    """
    # Try to get speed data
    speed_col = None
    for col in ['speed', 'enhanced_speed', 'session_avg_speed']:
        if col in df.columns:
            speed_col = col
            break
    
    if not speed_col:
        return {'stability_score': 0, 'degradation': 0}
    
    speed_data = df[speed_col].dropna()
    
    if len(speed_data) < 10:
        return {'stability_score': 0, 'degradation': 0}
    
    # Calculate pace degradation (slower over time)
    mid_point = len(speed_data) // 2
    first_half_avg = speed_data.iloc[:mid_point].mean()
    second_half_avg = speed_data.iloc[mid_point:].mean()
    degradation = first_half_avg - second_half_avg  # Positive = got slower
    
    # Convert to pace degradation (seconds per km)
    if first_half_avg > 0 and second_half_avg > 0:
        first_pace = (1000.0 / first_half_avg) / 60.0  # min/km
        second_pace = (1000.0 / second_half_avg) / 60.0  # min/km
        pace_degradation = second_pace - first_pace  # Positive = got slower
    else:
        pace_degradation = 0
    
    # Stability score: 0-100 (higher is better)
    # Good stability: pace degradation < 0.5 min/km
    stability_score = max(0, 100 - abs(pace_degradation) * 40)
    
    return {
        'stability_score': stability_score,
        'degradation': pace_degradation,
        'avg_speed': speed_data.mean()
    }


def score_long_run(df: pd.DataFrame) -> Tuple[str, Dict]:
    """
    Score a long run as A, B, or C.
    
    Returns:
        Tuple of (grade, analysis_dict)
    """
    hr_metrics = calculate_hr_stability(df)
    cadence_metrics = calculate_cadence_stability(df)
    pace_metrics = calculate_pace_stability(df)
    
    # Scoring criteria:
    # A Run: HR stable, Cadence stable, No significant degradation
    # B Run: HR drift but controlled, Minor form loss
    # C Run: HR + pace + cadence all degrade
    
    hr_stable = hr_metrics['cv'] < 8 and abs(hr_metrics['drift']) < 8
    cadence_stable = cadence_metrics['cv'] < 5 and abs(cadence_metrics['degradation']) < 3
    pace_stable = abs(pace_metrics['degradation']) < 0.5
    
    # Check for significant degradation (C run criteria)
    hr_degrading = abs(hr_metrics['drift']) > 15 or hr_metrics['cv'] > 12
    cadence_degrading = cadence_metrics['degradation'] < -5 or cadence_metrics['cv'] > 8
    pace_degrading = pace_metrics['degradation'] > 1.0
    
    hr_drift_controlled = abs(hr_metrics['drift']) < 15 and hr_metrics['cv'] < 12
    minor_form_loss = (not cadence_stable or not pace_stable) and not (cadence_degrading and pace_degrading)
    
    # Grade determination
    if hr_stable and cadence_stable and pace_stable:
        grade = 'A'
        recommendation = "Progress volume or terrain"
    elif hr_drift_controlled and minor_form_loss and not (hr_degrading and cadence_degrading and pace_degrading):
        grade = 'B'
        recommendation = "Repeat similar load"
    else:
        grade = 'C'
        recommendation = "Reduce load next week"
    
    analysis = {
        'grade': grade,
        'recommendation': recommendation,
        'hr_metrics': hr_metrics,
        'cadence_metrics': cadence_metrics,
        'pace_metrics': pace_metrics,
        'hr_stable': hr_stable,
        'cadence_stable': cadence_stable,
        'pace_stable': pace_stable
    }
    
    return grade, analysis


def analyze_long_run(csv_file: str) -> Dict:
    """
    Analyze a single long run file.
    
    Returns:
        Dictionary with analysis results
    """
    try:
        df = pd.read_csv(csv_file)
        
        # Get basic info
        distance = None
        if 'session_total_distance' in df.columns:
            distance = df['session_total_distance'].iloc[0] / 1000.0
        elif 'total_distance' in df.columns:
            distance = df['total_distance'].iloc[0] / 1000.0
        
        timestamp = None
        if 'session_start_time' in df.columns:
            timestamp = df['session_start_time'].iloc[0]
        elif 'timestamp' in df.columns:
            timestamp = df['timestamp'].iloc[0]
        
        # Score the run
        grade, analysis = score_long_run(df)
        
        return {
            'filename': os.path.basename(csv_file),
            'distance_km': distance,
            'timestamp': timestamp,
            'grade': grade,
            'analysis': analysis
        }
    except Exception as e:
        print(f"Error analyzing {csv_file}: {e}")
        return None


def generate_report(runs: List[Dict]) -> str:
    """
    Generate a formatted report for the long runs.
    
    Returns:
        Formatted report string
    """
    report = []
    report.append("🏃 LONG RUN QUALITY SCORING ANALYSIS")
    report.append("=" * 80)
    report.append("")
    report.append("Scoring Criteria:")
    report.append("  A Run: HR stable, Cadence stable, Legs recover in 24-36h")
    report.append("         ➡️ Progress volume or terrain")
    report.append("")
    report.append("  B Run: HR drift but controlled, Minor form loss")
    report.append("         ➡️ Repeat similar load")
    report.append("")
    report.append("  C Run: HR + pace + cadence all degrade")
    report.append("         ➡️ Reduce load next week")
    report.append("")
    report.append("=" * 80)
    report.append("")
    
    for i, run in enumerate(runs, 1):
        if run is None:
            continue
            
        report.append(f"RUN #{i}: {run['filename']}")
        report.append("-" * 80)
        report.append(f"Distance: {run['distance_km']:.2f} km")
        report.append(f"Date: {run['timestamp']}")
        report.append("")
        
        analysis = run['analysis']
        grade = analysis['grade']
        
        # Grade display
        grade_emoji = {'A': '🟢', 'B': '🟡', 'C': '🔴'}
        report.append(f"{grade_emoji[grade]} GRADE: {grade}")
        report.append(f"   Recommendation: {analysis['recommendation']}")
        report.append("")
        
        # HR Metrics
        hr = analysis['hr_metrics']
        report.append("💓 Heart Rate Analysis:")
        report.append(f"   Average HR: {hr['avg_hr']:.0f} bpm")
        report.append(f"   HR Range: {hr['min_hr']:.0f} - {hr['max_hr']:.0f} bpm")
        report.append(f"   Stability (CV): {hr['cv']:.1f}% {'✓' if hr['cv'] < 8 else '⚠'}")
        report.append(f"   HR Drift: {hr['drift']:+.1f} bpm {'✓' if abs(hr['drift']) < 8 else '⚠'}")
        report.append(f"   Status: {'Stable' if analysis['hr_stable'] else 'Drift detected'}")
        report.append("")
        
        # Cadence Metrics
        cad = analysis['cadence_metrics']
        report.append("👣 Cadence Analysis:")
        report.append(f"   Average Cadence: {cad['avg_cadence']:.0f} spm")
        report.append(f"   Stability (CV): {cad['cv']:.1f}% {'✓' if cad['cv'] < 5 else '⚠'}")
        report.append(f"   Degradation: {cad['degradation']:+.1f} spm {'✓' if cad['degradation'] < 3 else '⚠'}")
        report.append(f"   Status: {'Stable' if analysis['cadence_stable'] else 'Form loss detected'}")
        report.append("")
        
        # Pace Metrics
        pace = analysis['pace_metrics']
        report.append("⚡ Pace Analysis:")
        if pace['avg_speed']:
            avg_pace_min = (1000.0 / pace['avg_speed']) / 60.0
            report.append(f"   Average Pace: {int(avg_pace_min)}:{int((avg_pace_min - int(avg_pace_min)) * 60):02d}/km")
        report.append(f"   Pace Degradation: {pace['degradation']:+.2f} min/km {'✓' if abs(pace['degradation']) < 0.5 else '⚠'}")
        report.append(f"   Status: {'Stable' if analysis['pace_stable'] else 'Degradation detected'}")
        report.append("")
        
        report.append("=" * 80)
        report.append("")
    
    return "\n".join(report)


if __name__ == "__main__":
    running_folder = "/Users/hongtang/Documents/coros_fit/csv_folder/running"
    
    print("🔍 Finding 5 most recent long runs...")
    long_runs = get_long_runs(running_folder, min_distance_km=8.0, top_n=5)
    
    if not long_runs:
        print("No long runs found!")
        exit(1)
    
    print(f"Found {len(long_runs)} long runs")
    print("Analyzing...")
    print("")
    
    analyzed_runs = []
    for run_info in long_runs:
        analysis = analyze_long_run(run_info['file'])
        if analysis:
            analyzed_runs.append(analysis)
    
    # Generate report
    report = generate_report(analyzed_runs)
    print(report)
    
    # Save report
    output_file = "/Users/hongtang/Documents/coros_fit/long_run_analysis.txt"
    with open(output_file, 'w') as f:
        f.write(report)
    
    print(f"\n✅ Analysis saved to: {output_file}")
