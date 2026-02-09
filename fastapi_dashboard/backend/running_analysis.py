"""
Running-specific analysis for identifying strengths and gaps.

Analyzes running activities to provide coach insights on:
- Pace trends and consistency
- Heart rate zones and efficiency
- Training volume and distribution
- Workout variety
- Performance gaps
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from models import Activity, User
import statistics


def analyze_running_strengths_gaps(
    db: Session,
    user_id: int,
    days: int = 90
) -> Dict:
    """
    Analyze running activities to identify strengths and gaps.
    
    Args:
        db: Database session
        user_id: User ID
        days: Number of days to analyze (default: 90)
        
    Returns:
        Dictionary with analysis results including:
        - strengths: List of identified strengths
        - gaps: List of identified gaps
        - metrics: Detailed metrics for visualization
        - recommendations: Training recommendations
    """
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Fetch running activities
    activities = db.query(Activity).filter(
        and_(
            Activity.user_id == user_id,
            Activity.start_date >= start_date,
            Activity.start_date <= end_date,
            or_(
                func.lower(Activity.sport_type) == 'run',
                func.lower(Activity.type) == 'run'
            )
        )
    ).order_by(Activity.start_date).all()
    
    if not activities or len(activities) == 0:
        return {
            "strengths": [],
            "gaps": ["No running activities found in the selected period"],
            "metrics": {},
            "recommendations": ["Start logging running activities to get insights"],
            "total_runs": 0
        }
    
    # Extract metrics from activities
    runs = []
    for activity in activities:
        if not activity.start_date or not activity.distance_m:
            continue
        
        run_data = {
            "date": activity.start_date.date(),
            "distance_km": activity.distance_m / 1000.0,
            "duration_min": (activity.moving_time_s or activity.elapsed_time_s or 0) / 60.0,
            "pace_min_per_km": None,
            "avg_hr": activity.average_heartrate,
            "max_hr": activity.max_heartrate,
            "elevation_gain": activity.total_elevation_gain or 0
        }
        
        # Calculate pace
        if run_data["duration_min"] > 0 and run_data["distance_km"] > 0:
            run_data["pace_min_per_km"] = run_data["duration_min"] / run_data["distance_km"]
        
        runs.append(run_data)
    
    if not runs:
        return {
            "strengths": [],
            "gaps": ["Activities found but missing distance/time data"],
            "metrics": {},
            "recommendations": [],
            "total_runs": len(activities)
        }
    
    # Calculate aggregate metrics
    total_runs = len(runs)
    total_distance_km = sum(r["distance_km"] for r in runs)
    avg_distance_km = total_distance_km / total_runs if total_runs > 0 else 0
    
    # Pace analysis
    paces = [r["pace_min_per_km"] for r in runs if r["pace_min_per_km"] is not None]
    avg_pace = statistics.mean(paces) if paces else None
    pace_std = statistics.stdev(paces) if len(paces) > 1 else 0
    
    # Distance distribution
    short_runs = [r for r in runs if r["distance_km"] < 5]
    medium_runs = [r for r in runs if 5 <= r["distance_km"] < 15]
    long_runs = [r for r in runs if r["distance_km"] >= 15]
    
    # Heart rate analysis
    runs_with_hr = [r for r in runs if r["avg_hr"] is not None]
    avg_hr = statistics.mean([r["avg_hr"] for r in runs_with_hr]) if runs_with_hr else None
    
    # Elevation analysis
    runs_with_elevation = [r for r in runs if r["elevation_gain"] > 0]
    elevation_percentage = (len(runs_with_elevation) / total_runs * 100) if total_runs > 0 else 0
    
    # Frequency analysis
    dates = sorted([r["date"] for r in runs])
    if len(dates) > 1:
        date_range_days = (dates[-1] - dates[0]).days
        runs_per_week = (total_runs / date_range_days * 7) if date_range_days > 0 else 0
    else:
        runs_per_week = 0
    
    # Identify strengths
    strengths = []
    if total_runs >= 20:
        strengths.append(f"High consistency: {total_runs} runs in {days} days ({runs_per_week:.1f} runs/week)")
    elif total_runs >= 12:
        strengths.append(f"Good consistency: {total_runs} runs in {days} days")
    
    if avg_distance_km >= 8:
        strengths.append(f"Strong endurance base: Average {avg_distance_km:.1f} km per run")
    elif avg_distance_km >= 5:
        strengths.append(f"Building endurance: Average {avg_distance_km:.1f} km per run")
    
    if pace_std < 0.5 and avg_pace:
        strengths.append(f"Excellent pace consistency: {pace_std:.2f} min/km variation")
    elif pace_std < 1.0 and avg_pace:
        strengths.append(f"Good pace control: {pace_std:.2f} min/km variation")
    
    if len(long_runs) >= 3:
        strengths.append(f"Long run discipline: {len(long_runs)} runs ≥15km")
    
    if elevation_percentage > 30:
        strengths.append(f"Strong hill training: {elevation_percentage:.0f}% of runs include elevation")
    
    # Identify gaps
    gaps = []
    if total_runs < 12:
        gaps.append(f"Low frequency: Only {total_runs} runs in {days} days. Aim for 3-4 runs/week")
    
    if avg_distance_km < 5 and total_runs > 0:
        gaps.append(f"Short distances: Average {avg_distance_km:.1f} km. Build to 5-8km base runs")
    
    if len(long_runs) == 0 and total_runs >= 10:
        gaps.append("Missing long runs: No runs ≥15km. Add weekly long run for endurance")
    
    if len(short_runs) / total_runs > 0.8 if total_runs > 0 else False:
        gaps.append("Too many short runs: >80% are <5km. Add variety with longer base runs")
    
    if pace_std > 1.5 and avg_pace:
        gaps.append(f"Pace inconsistency: {pace_std:.2f} min/km variation. Focus on even pacing")
    
    if runs_per_week < 2 and total_runs > 0:
        gaps.append(f"Low frequency: {runs_per_week:.1f} runs/week. Increase to 3-4 for better adaptation")
    
    if elevation_percentage < 10 and total_runs >= 10:
        gaps.append("Limited hill work: <10% of runs have elevation. Add hills for strength")
    
    if not runs_with_hr or len(runs_with_hr) < total_runs * 0.5:
        gaps.append("Missing HR data: <50% of runs have heart rate. Use HR monitor for better insights")
    
    # Generate recommendations
    recommendations = []
    if len(gaps) > 0:
        top_gap = gaps[0]
        if "frequency" in top_gap.lower():
            recommendations.append("Increase running frequency to 3-4 times per week for better adaptation")
        elif "long run" in top_gap.lower():
            recommendations.append("Add one long run per week (15-20km) to build endurance")
        elif "pace" in top_gap.lower():
            recommendations.append("Focus on even pacing: Start slower, maintain consistent pace throughout")
        elif "distance" in top_gap.lower():
            recommendations.append("Gradually increase base run distance to 5-8km")
        elif "hill" in top_gap.lower():
            recommendations.append("Include 1-2 hilly runs per week to build leg strength")
        elif "hr" in top_gap.lower():
            recommendations.append("Use a heart rate monitor to track training intensity and recovery")
    
    # Prepare metrics for visualization
    metrics = {
        "total_runs": total_runs,
        "total_distance_km": round(total_distance_km, 1),
        "avg_distance_km": round(avg_distance_km, 2),
        "avg_pace_min_per_km": round(avg_pace, 2) if avg_pace else None,
        "pace_std": round(pace_std, 2),
        "runs_per_week": round(runs_per_week, 1),
        "short_runs_count": len(short_runs),
        "medium_runs_count": len(medium_runs),
        "long_runs_count": len(long_runs),
        "avg_hr": round(avg_hr, 0) if avg_hr else None,
        "elevation_percentage": round(elevation_percentage, 1),
        "runs": runs  # Full run data for time series
    }
    
    return {
        "strengths": strengths,
        "gaps": gaps,
        "metrics": metrics,
        "recommendations": recommendations,
        "total_runs": total_runs,
        "period_days": days
    }
