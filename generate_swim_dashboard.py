#!/usr/bin/env python3
"""
Generate a comprehensive swimming workout dashboard with scoring, analysis, and next workout prescription.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib.gridspec import GridSpec
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import argparse


def load_swim_data(csv_file: str) -> Tuple[pd.DataFrame, Dict]:
    """Load swimming workout data from CSV file and extract metadata."""
    df = pd.read_csv(csv_file)
    
    metadata = {}
    if 'session_start_time' in df.columns:
        metadata['date'] = df['session_start_time'].iloc[0]
    if 'session_total_distance' in df.columns:
        distance_m = df['session_total_distance'].iloc[0]
        metadata['distance_m'] = distance_m
        metadata['distance_km'] = distance_m / 1000.0
    if 'session_total_elapsed_time' in df.columns:
        metadata['total_time_sec'] = df['session_total_elapsed_time'].iloc[0]
    if 'session_pool_length' in df.columns:
        metadata['pool_length'] = df['session_pool_length'].iloc[0]
    if 'session_avg_cadence' in df.columns:
        metadata['avg_stroke_rate'] = df['session_avg_cadence'].iloc[0]
    if 'session_avg_speed' in df.columns:
        metadata['avg_speed_ms'] = df['session_avg_speed'].iloc[0]
    
    return df, metadata


def calculate_swim_metrics(df: pd.DataFrame) -> Dict:
    """Calculate all swimming-specific metrics for scoring."""
    metrics = {}
    
    # Get speed data (prefer enhanced_speed)
    speed_col = None
    for col in ['enhanced_speed', 'speed']:
        if col in df.columns:
            speed_col = col
            break
    
    if speed_col:
        speed_data = df[speed_col].dropna()
        speed_data = speed_data[speed_data > 0]  # Filter zeros (stops)
        if len(speed_data) > 0:
            metrics['speed'] = speed_data.values
            metrics['speed_avg'] = speed_data.mean()
            metrics['speed_std'] = speed_data.std()
            metrics['speed_cv'] = (speed_data.std() / speed_data.mean() * 100) if speed_data.mean() > 0 else 0
            
            # Detect stops (speed near zero)
            stop_threshold = speed_data.mean() * 0.1
            stops = (speed_data < stop_threshold).sum()
            metrics['num_stops'] = stops
            metrics['stop_percentage'] = (stops / len(speed_data) * 100) if len(speed_data) > 0 else 0
        else:
            metrics['speed'] = np.array([])
            metrics['speed_avg'] = 0
            metrics['speed_cv'] = 100
            metrics['stop_percentage'] = 100
    
    # Get stroke rate (cadence)
    if 'cadence' in df.columns:
        stroke_rate = df['cadence'].dropna()
        stroke_rate = stroke_rate[(stroke_rate > 0) & (stroke_rate < 100)]  # Reasonable range
        metrics['stroke_rate'] = stroke_rate.values
        if len(stroke_rate) > 0:
            metrics['stroke_rate_avg'] = stroke_rate.mean()
            metrics['stroke_rate_std'] = stroke_rate.std()
            metrics['stroke_rate_cv'] = (stroke_rate.std() / stroke_rate.mean() * 100) if stroke_rate.mean() > 0 else 0
            
            # Late stroke rate drop (last 20% vs first 20%)
            if len(stroke_rate) > 20:
                first_20 = stroke_rate.iloc[:len(stroke_rate)//5].mean()
                last_20 = stroke_rate.iloc[-len(stroke_rate)//5:].mean()
                metrics['stroke_rate_drop'] = first_20 - last_20
                metrics['stroke_rate_drop_pct'] = ((first_20 - last_20) / first_20 * 100) if first_20 > 0 else 0
    
    # Get distance segments (for continuous swim detection)
    if 'distance' in df.columns:
        distance = df['distance'].dropna()
        distance = distance[distance > 0]
        metrics['distance_segments'] = distance.values
    
    # Detect speed gears (fast segments)
    if 'speed' in metrics and len(metrics['speed']) > 50:
        speed_arr = metrics['speed']
        avg_speed = np.mean(speed_arr)
        # Look for segments >= 15% faster than average for at least 20 seconds
        fast_threshold = avg_speed * 1.15
        fast_segments = speed_arr >= fast_threshold
        
        # Count continuous fast segments (at least 20 consecutive points)
        in_fast_segment = False
        fast_segment_count = 0
        fast_segment_length = 0
        
        for i, is_fast in enumerate(fast_segments):
            if is_fast:
                if not in_fast_segment:
                    in_fast_segment = True
                    fast_segment_length = 1
                else:
                    fast_segment_length += 1
            else:
                if in_fast_segment and fast_segment_length >= 20:
                    fast_segment_count += 1
                in_fast_segment = False
                fast_segment_length = 0
        
        if in_fast_segment and fast_segment_length >= 20:
            fast_segment_count += 1
        
        metrics['speed_gear_count'] = fast_segment_count
        metrics['has_speed_gears'] = fast_segment_count > 0
    
    return metrics


def detect_workout_type(df: pd.DataFrame, metrics: Dict) -> str:
    """
    Detect workout type: Endurance / Threshold / Speed / Recovery / Technique
    """
    if 'speed' not in metrics or len(metrics['speed']) < 50:
        return "Recovery"
    
    speed = metrics['speed']
    stroke_rate = metrics.get('stroke_rate', np.array([]))
    
    # Calculate variability
    speed_cv = metrics.get('speed_cv', 0)
    avg_speed = metrics.get('speed_avg', 0)
    
    # Check for intervals (high variability, repeated patterns)
    if speed_cv > 15 and metrics.get('speed_gear_count', 0) > 3:
        return "Speed"
    
    # Check for threshold (moderate-fast, sustained)
    if avg_speed > 0.8 and speed_cv < 10:
        # Check if sustained (low stop percentage)
        if metrics.get('stop_percentage', 100) < 10:
            return "Threshold"
    
    # Check for technique (lots of stops, lower speed)
    if metrics.get('stop_percentage', 0) > 20:
        return "Technique"
    
    # Check for endurance (steady, moderate pace, low variability)
    if speed_cv < 8 and metrics.get('stop_percentage', 100) < 15:
        return "Endurance"
    
    # Default to recovery if low intensity
    if avg_speed < 0.6:
        return "Recovery"
    
    return "Endurance"  # Default


def score_swim_workout(metrics: Dict, workout_type: str) -> Tuple[str, Dict, int]:
    """
    Score swimming workout (A/B/C/D) and return sub-scores.
    
    Returns:
        (grade, sub_scores_dict, total_score_0_100)
    """
    sub_scores = {}
    
    # A) Distance Endurance (0-25)
    distance_score = 0
    distance_m = metrics.get('distance_m', 0)
    if distance_m > 0:
        # Simple heuristic: 2000m+ = excellent, 1500-2000 = good, 1000-1500 = ok, <1000 = poor
        if distance_m >= 2000:
            distance_score = 25
        elif distance_m >= 1500:
            distance_score = 20
        elif distance_m >= 1000:
            distance_score = 15
        elif distance_m >= 500:
            distance_score = 10
        else:
            distance_score = 5
    
    # Check for continuous blocks (low stop percentage)
    stop_pct = metrics.get('stop_percentage', 100)
    if stop_pct < 5:
        distance_score += 3
    elif stop_pct < 10:
        distance_score += 1
    
    distance_score = min(25, distance_score)
    sub_scores['distance_endurance'] = distance_score
    
    # B) Pace Consistency (0-25)
    pace_score = 0
    speed_cv = metrics.get('speed_cv', 100)
    if speed_cv < 3:
        pace_score = 25
    elif speed_cv < 6:
        pace_score = 20
    elif speed_cv < 10:
        pace_score = 15
    elif speed_cv < 15:
        pace_score = 10
    else:
        pace_score = 5
    
    # Penalize high stop percentage
    if stop_pct > 20:
        pace_score = max(0, pace_score - 5)
    
    sub_scores['pace_consistency'] = pace_score
    
    # C) Stroke Rate & Stability (0-25)
    stroke_score = 0
    stroke_cv = metrics.get('stroke_rate_cv', 100)
    stroke_drop = abs(metrics.get('stroke_rate_drop', 0))
    
    # Stroke rate stability
    if stroke_cv < 5:
        stroke_score = 15
    elif stroke_cv < 10:
        stroke_score = 12
    elif stroke_cv < 15:
        stroke_score = 8
    else:
        stroke_score = 5
    
    # Late drop penalty
    if stroke_drop < 2:
        stroke_score += 10
    elif stroke_drop < 4:
        stroke_score += 5
    elif stroke_drop > 5:
        stroke_score = max(0, stroke_score - 5)
    
    stroke_score = min(25, stroke_score)
    sub_scores['stroke_stability'] = stroke_score
    
    # D) Speed Gear Presence (0-25)
    speed_gear_score = 0
    has_gears = metrics.get('has_speed_gears', False)
    gear_count = metrics.get('speed_gear_count', 0)
    
    if gear_count >= 5:
        speed_gear_score = 25
    elif gear_count >= 3:
        speed_gear_score = 20
    elif gear_count >= 1:
        speed_gear_score = 15
    elif has_gears:
        speed_gear_score = 10
    else:
        # One-gear swim (endurance only)
        if workout_type == "Endurance":
            speed_gear_score = 15  # OK for endurance
        else:
            speed_gear_score = 5  # Missing speed for other types
    
    sub_scores['speed_gears'] = speed_gear_score
    
    # Calculate total score
    total_score = sum(sub_scores.values())
    
    # Map to grade
    if total_score >= 85:
        grade = "A"
    elif total_score >= 70:
        grade = "B"
    elif total_score >= 55:
        grade = "C"
    else:
        grade = "D"
    
    return grade, sub_scores, total_score


def generate_verdict(grade: str, sub_scores: Dict, workout_type: str, metrics: Dict) -> str:
    """Generate one-line verdict based on grade and metrics."""
    if grade == "A":
        return "Strong execution across all metrics — excellent session"
    elif grade == "B":
        # Identify the weak area
        min_score_key = min(sub_scores, key=sub_scores.get)
        if min_score_key == 'speed_gears':
            return "Strong aerobic base, speed gear missing"
        elif min_score_key == 'pace_consistency':
            return "Good effort, pacing needs more consistency"
        elif min_score_key == 'stroke_stability':
            return "Solid swim, stroke rate stability needs work"
        else:
            return "Good session with clear improvement areas"
    elif grade == "C":
        if metrics.get('stop_percentage', 0) > 20:
            return "Too many interruptions — focus on continuous swimming"
        elif metrics.get('speed_cv', 0) > 15:
            return "Pacing too chaotic — structure your sets better"
        else:
            return "Session completed but needs better structure"
    else:
        if metrics.get('stop_percentage', 0) > 30:
            return "Major breakdown — too many stops, unreliable data"
        else:
            return "Poor execution — focus on fundamentals"


def generate_pros_cons(metrics: Dict, sub_scores: Dict, workout_type: str) -> Tuple[List[str], List[str]]:
    """Generate 3 pros and 3 cons based on metrics."""
    pros = []
    cons = []
    
    # Pros
    if sub_scores['pace_consistency'] >= 20:
        pros.append("Excellent pacing control — consistent speed throughout")
    
    if sub_scores['distance_endurance'] >= 20:
        pros.append("Solid endurance base — you sustained volume well")
    
    if sub_scores['stroke_stability'] >= 20:
        pros.append("Stroke rhythm held up under fatigue — good form")
    
    if metrics.get('stop_percentage', 100) < 5:
        pros.append("Minimal interruptions — great continuous swimming")
    
    if sub_scores['speed_gears'] >= 20:
        pros.append("Good speed variation — multiple gears used effectively")
    
    # Fill remaining pros
    if len(pros) < 3:
        if metrics.get('distance_m', 0) > 1500:
            pros.append("Strong distance covered — building aerobic capacity")
        if metrics.get('stroke_rate_cv', 100) < 10:
            pros.append("Stable stroke rate — consistent technique")
    
    # Cons
    if sub_scores['speed_gears'] < 15 and workout_type != "Recovery":
        cons.append("One-gear swim — add speed gears for better stimulus")
    
    if metrics.get('stop_percentage', 0) > 15:
        cons.append("Too many interruptions — shorten rest, keep momentum")
    
    if sub_scores['pace_consistency'] < 15:
        cons.append("Pacing too variable — aim for more consistent splits")
    
    if metrics.get('stroke_rate_drop', 0) > 4:
        cons.append("Technique breaks late — add short form-focused repeats")
    
    if sub_scores['distance_endurance'] < 15:
        cons.append("Distance too short — build volume gradually")
    
    # Fill remaining cons
    if len(cons) < 3:
        if metrics.get('speed_cv', 0) > 12:
            cons.append("Speed variability too high — structure your sets")
        if metrics.get('stroke_rate_cv', 100) > 15:
            cons.append("Stroke rate inconsistent — focus on rhythm")
    
    # Ensure we have exactly 3 of each
    while len(pros) < 3:
        pros.append("Good effort — keep building consistency")
    while len(cons) < 3:
        cons.append("Room for improvement — focus on fundamentals")
    
    return pros[:3], cons[:3]


def prescribe_next_workout(grade: str, sub_scores: Dict, workout_type: str, metrics: Dict) -> Dict:
    """
    Prescribe the next workout based on current state.
    Returns dict with: main_set, key_focus, drill_set
    """
    # Identify the lowest sub-score (limiter)
    min_score_key = min(sub_scores, key=sub_scores.get)
    min_score = sub_scores[min_score_key]
    
    prescription = {}
    
    # Determine training priority
    if min_score_key == 'speed_gears' or (workout_type == "Endurance" and not metrics.get('has_speed_gears', False)):
        # Missing speed gears
        prescription['main_set'] = "12×100 @ moderate-hard, 20s rest\nCue: Hold stroke rate 34-36 spm, no over-glide"
        prescription['key_focus'] = "Speed gear development"
        prescription['drill_set'] = "8×25 fast (easy back) — focus on turnover"
        
    elif min_score_key == 'pace_consistency':
        # Pacing issues
        prescription['main_set'] = "6×200 @ controlled pace, 30s rest\nRule: Rep 1 must feel 'too easy'\nCue: Even splits > fast rep 1"
        prescription['key_focus'] = "Pacing control"
        prescription['drill_set'] = "4×50 build (easy to fast) — feel the pace change"
        
    elif min_score_key == 'stroke_stability':
        # Stroke rate issues
        prescription['main_set'] = "10×100 @ steady, 15s rest\nCue: Count strokes per length, maintain rhythm"
        prescription['key_focus'] = "Stroke rate consistency"
        prescription['drill_set'] = "6×50 with stroke count focus — efficiency over speed"
        
    elif min_score_key == 'distance_endurance':
        # Distance/endurance issues
        prescription['main_set'] = "3×500 continuous @ easy-moderate, 1 min rest\nCue: Build volume, maintain form"
        prescription['key_focus'] = "Aerobic base building"
        prescription['drill_set'] = "200 easy with focus on breathing rhythm"
        
    else:
        # Default progression
        if grade in ["A", "B"]:
            prescription['main_set'] = "8×150 @ threshold, 20s rest\nCue: Strong but controlled, negative split last 2"
            prescription['key_focus'] = "Threshold development"
            prescription['drill_set'] = "6×50 technique focus — streamline and catch"
        else:
            prescription['main_set'] = "5×200 @ aerobic, 30s rest\nCue: Steady effort, focus on form"
            prescription['key_focus'] = "Aerobic base"
            prescription['drill_set'] = "200 easy technique — long strokes"
    
    return prescription


def format_time(seconds: float) -> str:
    """Format time as HH:MM:SS or MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_speed(speed_ms: float) -> str:
    """Format speed as min/100m"""
    if speed_ms <= 0:
        return "N/A"
    pace_sec_per_100m = 100.0 / speed_ms
    minutes = int(pace_sec_per_100m // 60)
    seconds = int(pace_sec_per_100m % 60)
    return f"{minutes}:{seconds:02d}/100m"


def generate_dashboard(csv_file: str, output_file: str) -> None:
    """Generate the complete swimming dashboard."""
    # Load data
    df, metadata = load_swim_data(csv_file)
    metrics = calculate_swim_metrics(df)
    workout_type = detect_workout_type(df, metrics)
    
    # Add distance to metrics for scoring
    metrics['distance_m'] = metadata.get('distance_m', 0)
    
    # Score workout
    grade, sub_scores, total_score = score_swim_workout(metrics, workout_type)
    verdict = generate_verdict(grade, sub_scores, workout_type, metrics)
    pros, cons = generate_pros_cons(metrics, sub_scores, workout_type)
    prescription = prescribe_next_workout(grade, sub_scores, workout_type, metrics)
    
    # Create figure
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(5, 3, figure=fig, hspace=0.4, wspace=0.3,
                  left=0.05, right=0.95, top=0.95, bottom=0.05)
    
    # A. HEADER
    ax_header = fig.add_subplot(gs[0, :])
    ax_header.axis('off')
    
    date_str = metadata.get('date', 'Unknown')
    if isinstance(date_str, str) and len(date_str) > 10:
        date_str = date_str[:10]
    
    distance_m = metadata.get('distance_m', 0)
    time_sec = metadata.get('total_time_sec', 0)
    avg_speed = metadata.get('avg_speed_ms', 0)
    speed_cv = metrics.get('speed_cv', 0)
    stroke_rate = metadata.get('avg_stroke_rate', 0)
    
    header_text = f"""
Date: {date_str}  |  Sport: Swimming  |  Workout Type: {workout_type}
Total Distance: {distance_m:.0f}m  |  Total Time: {format_time(time_sec)}  |  Avg Pace: {format_speed(avg_speed)}  |  Variability: {speed_cv:.1f}%  |  Avg Stroke Rate: {stroke_rate:.0f} spm
Workout Goal: {workout_type}
"""
    ax_header.text(0.5, 0.5, header_text, ha='center', va='center',
                   fontsize=11, fontweight='bold', family='monospace',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))
    
    # B. OVERALL GRADE
    ax_grade = fig.add_subplot(gs[1, 0])
    ax_grade.axis('off')
    
    # Large grade letter
    grade_color = {'A': 'green', 'B': 'blue', 'C': 'orange', 'D': 'red'}.get(grade, 'black')
    ax_grade.text(0.5, 0.6, grade, ha='center', va='center',
                  fontsize=72, fontweight='bold', color=grade_color)
    ax_grade.text(0.5, 0.2, verdict, ha='center', va='center',
                  fontsize=10, family='monospace', wrap=True)
    ax_grade.text(0.5, 0.05, f"Score: {total_score}/100", ha='center', va='center',
                  fontsize=9, style='italic')
    
    # C. SUB-SCORES (Radar/Stacked Bar)
    ax_scores = fig.add_subplot(gs[1, 1:])
    
    categories = ['Distance\nEndurance', 'Pace\nConsistency', 'Stroke\nStability', 'Speed\nGears']
    scores = [sub_scores['distance_endurance'], sub_scores['pace_consistency'],
              sub_scores['stroke_stability'], sub_scores['speed_gears']]
    colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c']
    
    bars = ax_scores.barh(categories, scores, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax_scores.set_xlim(0, 25)
    ax_scores.set_xlabel('Score (out of 25)', fontsize=10, fontweight='bold')
    ax_scores.set_title('Sub-Scores Breakdown', fontsize=12, fontweight='bold', pad=10)
    ax_scores.grid(True, alpha=0.3, axis='x')
    
    # Add score labels on bars
    for i, (bar, score) in enumerate(zip(bars, scores)):
        width = bar.get_width()
        ax_scores.text(width + 0.5, bar.get_y() + bar.get_height()/2,
                      f'{score:.0f}', ha='left', va='center', fontweight='bold', fontsize=10)
    
    # D. PROS / CONS
    ax_pros_cons = fig.add_subplot(gs[2, :])
    ax_pros_cons.axis('off')
    
    pros_text = "PROS:\n" + "\n".join([f"  • {p}" for p in pros])
    cons_text = "CONS:\n" + "\n".join([f"  • {c}" for c in cons])
    
    ax_pros_cons.text(0.05, 0.95, pros_text, ha='left', va='top',
                      fontsize=10, family='monospace',
                      bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3),
                      transform=ax_pros_cons.transAxes)
    
    ax_pros_cons.text(0.55, 0.95, cons_text, ha='left', va='top',
                      fontsize=10, family='monospace',
                      bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.3),
                      transform=ax_pros_cons.transAxes)
    
    # E. CHARTS - Speed vs Time and Stroke Rate vs Speed
    ax_chart1 = fig.add_subplot(gs[3, :2])
    if 'speed' in metrics and len(metrics['speed']) > 0:
        speed = metrics['speed']
        time_elapsed = np.arange(len(speed))
        ax_chart1.plot(time_elapsed, speed, 'b-', linewidth=1, alpha=0.7)
        ax_chart1.set_xlabel('Time (samples)', fontsize=10, fontweight='bold')
        ax_chart1.set_ylabel('Speed (m/s)', fontsize=10, fontweight='bold', color='b')
        ax_chart1.tick_params(axis='y', labelcolor='b')
        ax_chart1.grid(True, alpha=0.3)
        ax_chart1.set_title('Speed vs Time', fontsize=11, fontweight='bold')
    
    ax_chart2 = fig.add_subplot(gs[3, 2])
    if 'speed' in metrics and 'stroke_rate' in metrics:
        speed = metrics['speed']
        stroke_rate = metrics['stroke_rate']
        min_len = min(len(speed), len(stroke_rate))
        if min_len > 0:
            scatter = ax_chart2.scatter(speed[:min_len], stroke_rate[:min_len],
                                       c=range(min_len), cmap='viridis', alpha=0.5, s=10)
            ax_chart2.set_xlabel('Speed (m/s)', fontsize=10, fontweight='bold')
            ax_chart2.set_ylabel('Stroke Rate (spm)', fontsize=10, fontweight='bold')
            ax_chart2.grid(True, alpha=0.3)
            ax_chart2.set_title('Stroke Rate vs Speed', fontsize=11, fontweight='bold')
    
    # F. PRESCRIBED NEXT WORKOUT
    ax_prescription = fig.add_subplot(gs[4, :])
    ax_prescription.axis('off')
    
    prescription_text = f"""
PRESCRIBED NEXT WORKOUT:

Main Set:
{prescription['main_set']}

1 Key Focus: {prescription['key_focus']}

Drill Set: {prescription['drill_set']}
"""
    
    ax_prescription.text(0.05, 0.95, prescription_text, ha='left', va='top',
                        fontsize=11, family='monospace', fontweight='bold',
                        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5),
                        transform=ax_prescription.transAxes)
    
    # Save
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ Dashboard saved to: {output_file}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Generate swimming workout dashboard')
    parser.add_argument('csv_file', help='Path to swimming CSV workout file')
    parser.add_argument('-o', '--output', help='Output file path (default: dashboard_<filename>.png)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"❌ Error: File not found: {args.csv_file}")
        sys.exit(1)
    
    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(os.path.basename(args.csv_file))[0]
        output_file = f"swim_dashboard_{base_name}.png"
    
    generate_dashboard(args.csv_file, output_file)


if __name__ == "__main__":
    main()
