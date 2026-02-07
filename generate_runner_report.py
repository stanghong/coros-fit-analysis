#!/usr/bin/env python3
"""
Generate a one-page runner report from CSV workout data.
Reusable template for key workouts (quality runs or long runs).
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.gridspec import GridSpec
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import argparse


def load_workout_data(csv_file: str) -> Tuple[pd.DataFrame, Dict]:
    """
    Load workout data from CSV file and extract metadata.
    
    Returns:
        Tuple of (dataframe, metadata_dict)
    """
    df = pd.read_csv(csv_file)
    
    # Extract metadata from first row
    metadata = {}
    if 'session_start_time' in df.columns:
        metadata['date'] = df['session_start_time'].iloc[0]
    if 'session_total_distance' in df.columns:
        distance_m = df['session_total_distance'].iloc[0]
        metadata['distance_km'] = distance_m / 1000.0 if distance_m > 100 else distance_m
    if 'session_total_elapsed_time' in df.columns:
        metadata['total_time_sec'] = df['session_total_elapsed_time'].iloc[0]
    if 'session_avg_heart_rate' in df.columns:
        metadata['avg_hr'] = df['session_avg_heart_rate'].iloc[0]
    if 'session_max_heart_rate' in df.columns:
        metadata['max_hr'] = df['session_max_heart_rate'].iloc[0]
    if 'session_avg_running_cadence' in df.columns:
        metadata['avg_cadence'] = df['session_avg_running_cadence'].iloc[0]
    if 'session_avg_speed' in df.columns:
        speed_ms = df['session_avg_speed'].iloc[0]
        if speed_ms > 0:
            metadata['avg_pace_min_per_km'] = (1000.0 / speed_ms) / 60.0
    
    return df, metadata


def calculate_metrics(df: pd.DataFrame) -> Dict:
    """Calculate all workout metrics for the report."""
    metrics = {}
    
    # Get speed/pace data
    speed_col = None
    for col in ['enhanced_speed', 'speed']:
        if col in df.columns:
            speed_col = col
            break
    
    if speed_col:
        speed_data = df[speed_col].dropna()
        speed_data = speed_data[speed_data > 0]
        if len(speed_data) > 0:
            pace_data = (1000.0 / speed_data) / 60.0  # min/km
            pace_data = pace_data[pace_data < 30]  # Filter outliers
            metrics['pace'] = pace_data.values
            metrics['time_elapsed'] = np.arange(len(pace_data))
    
    # Get HR data
    if 'heart_rate' in df.columns:
        hr_data = df['heart_rate'].dropna()
        hr_data = hr_data[(hr_data > 0) & (hr_data < 220)]
        metrics['heart_rate'] = hr_data.values
        if len(hr_data) > 0:
            metrics['avg_hr'] = hr_data.mean()
            metrics['max_hr'] = hr_data.max()
            metrics['min_hr'] = hr_data.min()
            
            # Calculate HR drift (first 25% vs last 25%)
            if len(hr_data) > 20:
                first_quarter = hr_data.iloc[:len(hr_data)//4].mean()
                last_quarter = hr_data.iloc[-len(hr_data)//4:].mean()
                metrics['hr_drift'] = last_quarter - first_quarter
                metrics['hr_drift_pct'] = ((last_quarter - first_quarter) / first_quarter * 100) if first_quarter > 0 else 0
    
    # Get cadence data
    if 'cadence' in df.columns:
        cadence_data = df['cadence'].dropna()
        cadence_data = cadence_data[(cadence_data > 0) & (cadence_data < 250)]
        metrics['cadence'] = cadence_data.values
        if len(cadence_data) > 0:
            metrics['avg_cadence'] = cadence_data.mean()
            metrics['cadence_std'] = cadence_data.std()
            
            # Check for late-run cadence drop (last 25% vs first 25%)
            if len(cadence_data) > 20:
                first_quarter = cadence_data.iloc[:len(cadence_data)//4].mean()
                last_quarter = cadence_data.iloc[-len(cadence_data)//4:].mean()
                metrics['cadence_drop'] = first_quarter - last_quarter
    
    # Get step length
    if 'step_length' in df.columns:
        step_data = df['step_length'].dropna()
        step_data = step_data[step_data > 0]
        if len(step_data) > 0:
            metrics['avg_step_length'] = step_data.mean()
    
    # Calculate efficiency (pace at HR)
    if 'pace' in metrics and 'heart_rate' in metrics:
        pace_arr = metrics['pace']
        hr_arr = metrics['heart_rate']
        min_len = min(len(pace_arr), len(hr_arr))
        if min_len > 10:
            # Calculate correlation
            metrics['hr_pace_correlation'] = np.corrcoef(hr_arr[:min_len], pace_arr[:min_len])[0, 1]
            
            # Calculate efficiency score (lower HR at same pace = better)
            # Use median pace and HR for reference
            median_pace = np.median(pace_arr)
            median_hr = np.median(hr_arr)
            if median_pace > 0 and median_hr > 0:
                metrics['efficiency_score'] = median_hr / median_pace  # Lower is better
    
    return metrics


def detect_intervals(df: pd.DataFrame, metrics: Dict) -> Optional[List[Dict]]:
    """
    Detect intervals or segments in the workout.
    Looks for repeated patterns of high/low pace or HR.
    """
    if 'pace' not in metrics or len(metrics['pace']) < 50:
        return None
    
    pace = metrics['pace']
    hr = metrics.get('heart_rate', np.array([]))
    cadence = metrics.get('cadence', np.array([]))
    
    # Simple interval detection: look for significant pace variations
    # Group into segments based on pace changes
    segments = []
    num_segments = 8
    segment_length = len(pace) // num_segments
    
    for i in range(0, len(pace), segment_length):
        if i + segment_length <= len(pace):
            segment_pace = pace[i:i+segment_length]
            seg_data = {
                'rep': len(segments) + 1,
                'pace_avg': np.mean(segment_pace),
                'pace_min': np.min(segment_pace),
                'pace_max': np.max(segment_pace),
            }
            
            if len(hr) > i + segment_length:
                seg_hr = hr[i:i+segment_length]
                seg_data['hr_avg'] = np.mean(seg_hr)
                seg_data['hr_max'] = np.max(seg_hr)
            
            if len(cadence) > i + segment_length:
                seg_cad = cadence[i:i+segment_length]
                seg_data['cadence_avg'] = np.mean(seg_cad)
            
            segments.append(seg_data)
    
    return segments if len(segments) > 1 else None


def format_pace(pace_min_per_km: float) -> str:
    """Format pace as MM:SS/km"""
    minutes = int(pace_min_per_km)
    seconds = int((pace_min_per_km - minutes) * 60)
    return f"{minutes}:{seconds:02d}"


def format_time(seconds: float) -> str:
    """Format time as HH:MM:SS or MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def calculate_execution_score(metrics: Dict) -> str:
    """Calculate execution score (A/B/C) based on HR drift, cadence stability, pace stability."""
    score = 0
    
    # HR drift check
    if 'hr_drift_pct' in metrics:
        if abs(metrics['hr_drift_pct']) < 5:
            score += 2  # Excellent
        elif abs(metrics['hr_drift_pct']) < 10:
            score += 1  # Good
    
    # Cadence stability
    if 'cadence_std' in metrics and 'avg_cadence' in metrics:
        cv = (metrics['cadence_std'] / metrics['avg_cadence'] * 100) if metrics['avg_cadence'] > 0 else 100
        if cv < 5:
            score += 2
        elif cv < 10:
            score += 1
    
    # Cadence drop check
    if 'cadence_drop' in metrics:
        if metrics['cadence_drop'] < 2:
            score += 1
    
    if score >= 4:
        return 'A'
    elif score >= 2:
        return 'B'
    else:
        return 'C'


def generate_report(csv_file: str, output_file: str, 
                   workout_type: str = "Long",
                   route: str = "Flat",
                   weather: str = "",
                   shoes: str = "",
                   fatigue_context: str = "Medium") -> None:
    """
    Generate a one-page runner report.
    
    Args:
        csv_file: Path to CSV workout file
        output_file: Path to save the report (PDF or PNG)
        workout_type: Type of workout (Easy/Tempo/Intervals/Long/Trail)
        route: Route type (Flat/Rolling/Trail)
        weather: Weather conditions (Temp/Humidity/Wind)
        shoes: Shoes used
        fatigue_context: Fatigue level (Fresh/Medium/Tired)
    """
    # Load data
    df, metadata = load_workout_data(csv_file)
    metrics = calculate_metrics(df)
    intervals = detect_intervals(df, metrics)
    
    # Create figure with custom layout
    fig = plt.figure(figsize=(16, 11))  # A4 landscape-ish
    gs = GridSpec(6, 3, figure=fig, hspace=0.4, wspace=0.3,
                  left=0.05, right=0.95, top=0.95, bottom=0.05)
    
    # HEADER - Workout Context (Top Strip)
    ax_header = fig.add_subplot(gs[0, :])
    ax_header.axis('off')
    
    date_str = metadata.get('date', 'Unknown')
    if isinstance(date_str, str) and len(date_str) > 10:
        date_str = date_str[:10]
    
    header_text = f"""
Date: {date_str}  |  Workout Type: {workout_type}  |  Route: {route}  |  Weather: {weather}  |  Shoes: {shoes}  |  Fatigue Context: {fatigue_context}
"""
    ax_header.text(0.5, 0.5, header_text, ha='center', va='center',
                   fontsize=11, fontweight='bold', family='monospace',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))
    
    # PANEL 1 - Pace & Heart Rate Over Time
    ax1 = fig.add_subplot(gs[1, :2])
    if 'pace' in metrics and 'heart_rate' in metrics:
        pace = metrics['pace']
        hr = metrics['heart_rate']
        
        # Align arrays to same length
        min_len = min(len(pace), len(hr))
        pace_aligned = pace[:min_len]
        hr_aligned = hr[:min_len]
        time_elapsed = np.arange(min_len)
        
        # Normalize for dual axis
        ax1_twin = ax1.twinx()
        
        # Plot pace
        line1 = ax1.plot(time_elapsed, pace_aligned, 'b-', linewidth=1.5, label='Pace (min/km)', alpha=0.7)
        ax1.set_xlabel('Time (samples)', fontsize=10, fontweight='bold')
        ax1.set_ylabel('Pace (min/km)', color='b', fontsize=10, fontweight='bold')
        ax1.tick_params(axis='y', labelcolor='b')
        ax1.grid(True, alpha=0.3)
        ax1.invert_yaxis()  # Faster pace (lower) at top
        
        # Plot HR
        line2 = ax1_twin.plot(time_elapsed, hr_aligned, 'r-', linewidth=1.5, label='Heart Rate (bpm)', alpha=0.7)
        ax1_twin.set_ylabel('Heart Rate (bpm)', color='r', fontsize=10, fontweight='bold')
        ax1_twin.tick_params(axis='y', labelcolor='r')
        
        # Combine legends
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper left', fontsize=9)
        
        ax1.set_title('PANEL 1: Pace & Heart Rate Over Time', fontsize=11, fontweight='bold', pad=10)
    
    # PANEL 2 - HR vs Pace (Efficiency Map)
    ax2 = fig.add_subplot(gs[1, 2])
    if 'pace' in metrics and 'heart_rate' in metrics:
        pace = metrics['pace']
        hr = metrics['heart_rate']
        min_len = min(len(pace), len(hr))
        
        # Ensure we have valid data
        if min_len > 0:
            hr_valid = hr[:min_len]
            pace_valid = pace[:min_len]
            
            scatter = ax2.scatter(hr_valid, pace_valid, c=range(min_len),
                                cmap='viridis', alpha=0.5, s=10, edgecolors='none')
            
            ax2.set_xlabel('Heart Rate (bpm)', fontsize=10, fontweight='bold')
            ax2.set_ylabel('Pace (min/km)', fontsize=10, fontweight='bold')
            ax2.invert_yaxis()
            ax2.grid(True, alpha=0.3)
            ax2.set_title('PANEL 2: HR vs Pace\n(Efficiency Map)', fontsize=11, fontweight='bold', pad=10)
            
            # Add trend line
            if min_len > 10:
                z = np.polyfit(hr_valid, pace_valid, 1)
                p = np.poly1d(z)
                hr_range = np.linspace(hr_valid.min(), hr_valid.max(), 100)
                ax2.plot(hr_range, p(hr_range), "r--", alpha=0.5, linewidth=2, label='Trend')
                ax2.legend(fontsize=8)
    
    # PANEL 3 - Cadence & Form Stability
    ax3 = fig.add_subplot(gs[2, 0])
    ax3.axis('off')
    
    cadence_text = "PANEL 3: Cadence & Form Stability\n\n"
    if 'avg_cadence' in metrics:
        cadence_text += f"Avg Cadence: {metrics['avg_cadence']:.1f} spm\n"
    if 'cadence_std' in metrics:
        cadence_text += f"Cadence Std Dev: {metrics['cadence_std']:.1f} spm\n"
    if 'avg_step_length' in metrics:
        cadence_text += f"Step Length Avg: {metrics['avg_step_length']:.0f} mm\n"
    if 'cadence_drop' in metrics:
        drop_status = "Yes" if metrics['cadence_drop'] > 2 else "No"
        cadence_text += f"Late-run Cadence Drop: {drop_status}\n"
    else:
        cadence_text += "Late-run Cadence Drop: N/A\n"
    
    ax3.text(0.1, 0.5, cadence_text, ha='left', va='center',
             fontsize=10, family='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    # PANEL 4 - Interval/Segment Table
    ax4 = fig.add_subplot(gs[2, 1:])
    ax4.axis('off')
    
    table_text = "PANEL 4: Interval / Segment Table\n\n"
    if intervals and len(intervals) > 0:
        table_text += "Rep    Pace        HR Avg    HR Max    Cadence\n"
        table_text += "-" * 50 + "\n"
        for seg in intervals[:8]:  # Limit to 8 segments
            pace_str = format_pace(seg['pace_avg'])
            hr_avg_str = f"{seg.get('hr_avg', 0):.0f}" if 'hr_avg' in seg else "N/A"
            hr_max_str = f"{seg.get('hr_max', 0):.0f}" if 'hr_max' in seg else "N/A"
            cad_str = f"{seg.get('cadence_avg', 0):.0f}" if 'cadence_avg' in seg else "N/A"
            table_text += f"{seg['rep']:<7}{pace_str}/km{'':<4}{hr_avg_str:<10}{hr_max_str:<10}{cad_str}\n"
    else:
        table_text += "No clear intervals detected.\n"
        table_text += "Workout appears to be steady-state.\n"
    
    ax4.text(0.05, 0.5, table_text, ha='left', va='center',
             fontsize=9, family='monospace',
             bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))
    
    # PANEL 5 - Key Summary Metrics
    ax5 = fig.add_subplot(gs[3, :])
    ax5.axis('off')
    
    total_time = metadata.get('total_time_sec', 0)
    distance = metadata.get('distance_km', 0)
    avg_pace = metadata.get('avg_pace_min_per_km', 0)
    if avg_pace == 0 and 'pace' in metrics:
        avg_pace = np.mean(metrics['pace'])
    
    summary_text = "PANEL 5: Key Summary Metrics\n\n"
    summary_text += f"Total Time: {format_time(total_time)}\n"
    summary_text += f"Total Distance: {distance:.2f} km\n"
    summary_text += f"Avg Pace: {format_pace(avg_pace)}/km\n"
    
    if 'avg_hr' in metrics:
        summary_text += f"Avg HR: {metrics['avg_hr']:.0f} bpm\n"
    if 'hr_drift_pct' in metrics:
        summary_text += f"HR Drift %: {metrics['hr_drift_pct']:+.1f}%\n"
    if 'efficiency_score' in metrics:
        summary_text += f"Efficiency Score: {metrics['efficiency_score']:.1f} (pace @ HR)\n"
    
    execution_score = calculate_execution_score(metrics)
    summary_text += f"Execution Score: {execution_score}\n"
    
    ax5.text(0.1, 0.5, summary_text, ha='left', va='center',
             fontsize=11, family='monospace', fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    
    # PANEL 6 - Coach Notes (MOST IMPORTANT)
    ax6 = fig.add_subplot(gs[4:, :])
    ax6.axis('off')
    
    notes_text = """PANEL 6: Coach Notes (MOST IMPORTANT)

What went well:
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

What broke down:
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

Key limiter (legs / aerobic / pacing / fueling):
_________________________________________________________________
_________________________________________________________________

Next adjustment:
_________________________________________________________________
_________________________________________________________________

If you only write 3 sentences here, you're already ahead of 95% of runners.
"""
    
    ax6.text(0.05, 0.95, notes_text, ha='left', va='top',
             fontsize=10, family='monospace',
             bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.3))
    
    # Add interpretation hints
    interpretation_text = """
COACH INTERPRETATION GUIDE:

Panel 1: Smooth oscillations = good execution | HR drift but pace holds = aerobic fatigue | Pace fades + HR rises = overreached
Panel 2: Tight diagonal cluster = efficient | Right-shift vs last week = fatigue or heat | Same HR, faster pace = fitness gain
Panel 3: Cadence stability > cadence number | Cadence collapse late = risk for 100K breakdown
Panel 4: Look for drift across reps | HR recovery quality | Form degradation
"""
    
    ax6.text(0.55, 0.95, interpretation_text, ha='left', va='top',
             fontsize=8, family='monospace', style='italic',
             bbox=dict(boxstyle='round', facecolor='lavender', alpha=0.3))
    
    # Save figure
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ Report saved to: {output_file}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Generate one-page runner report from CSV workout data')
    parser.add_argument('csv_file', help='Path to CSV workout file')
    parser.add_argument('-o', '--output', help='Output file path (default: report_<filename>.png)')
    parser.add_argument('--workout-type', default='Long', choices=['Easy', 'Tempo', 'Intervals', 'Long', 'Trail'],
                       help='Workout type')
    parser.add_argument('--route', default='Flat', choices=['Flat', 'Rolling', 'Trail'],
                       help='Route type')
    parser.add_argument('--weather', default='', help='Weather conditions (e.g., "20C 60pct 5kmh")')
    parser.add_argument('--shoes', default='', help='Shoes used')
    parser.add_argument('--fatigue', default='Medium', choices=['Fresh', 'Medium', 'Tired'],
                       help='Fatigue context')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"❌ Error: File not found: {args.csv_file}")
        sys.exit(1)
    
    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(os.path.basename(args.csv_file))[0]
        output_file = f"report_{base_name}.png"
    
    generate_report(
        csv_file=args.csv_file,
        output_file=output_file,
        workout_type=args.workout_type,
        route=args.route,
        weather=args.weather,
        shoes=args.shoes,
        fatigue_context=args.fatigue
    )


if __name__ == "__main__":
    main()
