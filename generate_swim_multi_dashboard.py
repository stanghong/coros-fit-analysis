#!/usr/bin/env python3
"""
Generate a comprehensive dashboard visualizing the last 10 swimming workouts.
Shows trends, comparisons, and overall progress.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import argparse
import glob

# Import functions from the single workout dashboard
from generate_swim_dashboard import (
    load_swim_data, calculate_swim_metrics, detect_workout_type,
    score_swim_workout, format_time, format_speed
)


def get_recent_swim_files(swimming_folder: str, n: int = 10) -> List[str]:
    """Get the n most recent swimming CSV files."""
    csv_files = glob.glob(os.path.join(swimming_folder, "*.csv"))
    
    # Sort by modification time (most recent first)
    csv_files.sort(key=os.path.getmtime, reverse=True)
    
    return csv_files[:n]


def analyze_all_workouts(csv_files: List[str]) -> List[Dict]:
    """Analyze all workout files and return list of analysis dicts."""
    all_workouts = []
    
    for csv_file in csv_files:
        try:
            df, metadata = load_swim_data(csv_file)
            metrics = calculate_swim_metrics(df)
            workout_type = detect_workout_type(df, metrics)
            grade, sub_scores, total_score = score_swim_workout(metrics, workout_type)
            
            # Add metadata
            metrics['distance_m'] = metadata.get('distance_m', 0)
            metrics['total_time_sec'] = metadata.get('total_time_sec', 0)
            metrics['date'] = metadata.get('date', 'Unknown')
            metrics['avg_speed_ms'] = metadata.get('avg_speed_ms', 0)
            metrics['avg_stroke_rate'] = metadata.get('avg_stroke_rate', 0)
            
            workout_analysis = {
                'file': os.path.basename(csv_file),
                'date': metadata.get('date', 'Unknown'),
                'metadata': metadata,
                'metrics': metrics,
                'workout_type': workout_type,
                'grade': grade,
                'sub_scores': sub_scores,
                'total_score': total_score
            }
            
            all_workouts.append(workout_analysis)
        except Exception as e:
            print(f"Warning: Could not analyze {csv_file}: {e}")
            continue
    
    return all_workouts


def generate_multi_dashboard(workouts: List[Dict], output_file: str) -> None:
    """Generate dashboard showing all workouts."""
    if len(workouts) == 0:
        print("❌ No workouts to display")
        return
    
    # Sort by date (most recent first)
    workouts.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    fig = plt.figure(figsize=(20, 14))
    gs = GridSpec(4, 4, figure=fig, hspace=0.5, wspace=0.4,
                  left=0.05, right=0.95, top=0.95, bottom=0.05)
    
    # Extract data for plotting
    dates = []
    distances = []
    times = []
    speeds = []
    stroke_rates = []
    grades = []
    total_scores = []
    sub_scores_list = []
    workout_types = []
    
    for w in workouts:
        date_str = w.get('date', 'Unknown')
        if isinstance(date_str, str) and len(date_str) > 10:
            date_str = date_str[:10]
        dates.append(date_str)
        
        distances.append(w['metrics'].get('distance_m', 0))
        times.append(w['metrics'].get('total_time_sec', 0) / 60)  # minutes
        speeds.append(w['metrics'].get('avg_speed_ms', 0))
        stroke_rates.append(w['metrics'].get('avg_stroke_rate', 0))
        grades.append(w['grade'])
        total_scores.append(w['total_score'])
        sub_scores_list.append(w['sub_scores'])
        workout_types.append(w['workout_type'])
    
    # Convert dates to numeric for plotting
    date_nums = list(range(len(dates)))
    
    # HEADER
    ax_header = fig.add_subplot(gs[0, :])
    ax_header.axis('off')
    
    total_distance = sum(distances)
    total_time = sum(times)
    avg_score = np.mean(total_scores) if total_scores else 0
    
    header_text = f"""
SWIMMING WORKOUT DASHBOARD - Last {len(workouts)} Workouts
Total Distance: {total_distance:.0f}m  |  Total Time: {total_time:.0f} min  |  Average Score: {avg_score:.1f}/100
"""
    ax_header.text(0.5, 0.5, header_text, ha='center', va='center',
                   fontsize=14, fontweight='bold', family='monospace',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))
    
    # CHART 1: Distance Over Time
    ax1 = fig.add_subplot(gs[1, 0])
    ax1.bar(date_nums, distances, color='steelblue', alpha=0.7, edgecolor='black')
    ax1.set_xlabel('Workout #', fontsize=10, fontweight='bold')
    ax1.set_ylabel('Distance (m)', fontsize=10, fontweight='bold')
    ax1.set_title('Distance per Workout', fontsize=11, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.set_xticks(date_nums)
    ax1.set_xticklabels([f"#{i+1}" for i in range(len(dates))], rotation=45, ha='right')
    
    # CHART 2: Total Score Over Time
    ax2 = fig.add_subplot(gs[1, 1])
    colors = {'A': 'green', 'B': 'blue', 'C': 'orange', 'D': 'red'}
    bar_colors = [colors.get(g, 'gray') for g in grades]
    ax2.bar(date_nums, total_scores, color=bar_colors, alpha=0.7, edgecolor='black')
    ax2.axhline(y=85, color='green', linestyle='--', alpha=0.5, label='A threshold')
    ax2.axhline(y=70, color='blue', linestyle='--', alpha=0.5, label='B threshold')
    ax2.axhline(y=55, color='orange', linestyle='--', alpha=0.5, label='C threshold')
    ax2.set_xlabel('Workout #', fontsize=10, fontweight='bold')
    ax2.set_ylabel('Total Score', fontsize=10, fontweight='bold')
    ax2.set_title('Workout Scores Over Time', fontsize=11, fontweight='bold')
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.set_xticks(date_nums)
    ax2.set_xticklabels([f"#{i+1}" for i in range(len(dates))], rotation=45, ha='right')
    ax2.legend(fontsize=8, loc='upper right')
    
    # CHART 3: Sub-Scores Comparison (Stacked Area or Grouped Bar)
    ax3 = fig.add_subplot(gs[1, 2:])
    
    # Prepare sub-score data
    distance_scores = [s['distance_endurance'] for s in sub_scores_list]
    pace_scores = [s['pace_consistency'] for s in sub_scores_list]
    stroke_scores = [s['stroke_stability'] for s in sub_scores_list]
    gear_scores = [s['speed_gears'] for s in sub_scores_list]
    
    x = np.arange(len(date_nums))
    width = 0.2
    
    ax3.bar(x - 1.5*width, distance_scores, width, label='Distance', color='#2ecc71', alpha=0.7)
    ax3.bar(x - 0.5*width, pace_scores, width, label='Pace', color='#3498db', alpha=0.7)
    ax3.bar(x + 0.5*width, stroke_scores, width, label='Stroke', color='#9b59b6', alpha=0.7)
    ax3.bar(x + 1.5*width, gear_scores, width, label='Speed Gears', color='#e74c3c', alpha=0.7)
    
    ax3.set_xlabel('Workout #', fontsize=10, fontweight='bold')
    ax3.set_ylabel('Sub-Score (out of 25)', fontsize=10, fontweight='bold')
    ax3.set_title('Sub-Scores Breakdown', fontsize=11, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels([f"#{i+1}" for i in range(len(dates))], rotation=45, ha='right')
    ax3.legend(fontsize=9, loc='upper right')
    ax3.set_ylim(0, 25)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # CHART 4: Average Speed Over Time
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.plot(date_nums, speeds, 'o-', color='darkblue', linewidth=2, markersize=8)
    ax4.set_xlabel('Workout #', fontsize=10, fontweight='bold')
    ax4.set_ylabel('Avg Speed (m/s)', fontsize=10, fontweight='bold')
    ax4.set_title('Average Speed Trend', fontsize=11, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.set_xticks(date_nums)
    ax4.set_xticklabels([f"#{i+1}" for i in range(len(dates))], rotation=45, ha='right')
    
    # CHART 5: Stroke Rate Over Time
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.plot(date_nums, stroke_rates, 'o-', color='purple', linewidth=2, markersize=8)
    ax5.set_xlabel('Workout #', fontsize=10, fontweight='bold')
    ax5.set_ylabel('Avg Stroke Rate (spm)', fontsize=10, fontweight='bold')
    ax5.set_title('Stroke Rate Trend', fontsize=11, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    ax5.set_xticks(date_nums)
    ax5.set_xticklabels([f"#{i+1}" for i in range(len(dates))], rotation=45, ha='right')
    
    # CHART 6: Workout Type Distribution
    ax6 = fig.add_subplot(gs[2, 2])
    type_counts = {}
    for wt in workout_types:
        type_counts[wt] = type_counts.get(wt, 0) + 1
    
    types = list(type_counts.keys())
    counts = list(type_counts.values())
    colors_pie = {'Endurance': '#2ecc71', 'Threshold': '#3498db', 'Speed': '#e74c3c',
                  'Recovery': '#f39c12', 'Technique': '#9b59b6'}
    pie_colors = [colors_pie.get(t, 'gray') for t in types]
    
    ax6.pie(counts, labels=types, autopct='%1.1f%%', colors=pie_colors, startangle=90)
    ax6.set_title('Workout Type Distribution', fontsize=11, fontweight='bold')
    
    # CHART 7: Grade Distribution
    ax7 = fig.add_subplot(gs[2, 3])
    grade_counts = {}
    for g in grades:
        grade_counts[g] = grade_counts.get(g, 0) + 1
    
    grade_labels = ['A', 'B', 'C', 'D']
    grade_values = [grade_counts.get(g, 0) for g in grade_labels]
    grade_colors = [colors.get(g, 'gray') for g in grade_labels]
    
    ax7.bar(grade_labels, grade_values, color=grade_colors, alpha=0.7, edgecolor='black')
    ax7.set_xlabel('Grade', fontsize=10, fontweight='bold')
    ax7.set_ylabel('Count', fontsize=10, fontweight='bold')
    ax7.set_title('Grade Distribution', fontsize=11, fontweight='bold')
    ax7.grid(True, alpha=0.3, axis='y')
    
    # TABLE: Summary of All Workouts
    ax_table = fig.add_subplot(gs[3, :])
    ax_table.axis('off')
    
    # Create table data
    table_data = []
    for i, w in enumerate(workouts):
        date_str = w.get('date', 'Unknown')
        if isinstance(date_str, str) and len(date_str) > 10:
            date_str = date_str[:10]
        
        distance = w['metrics'].get('distance_m', 0)
        time_min = w['metrics'].get('total_time_sec', 0) / 60
        speed = w['metrics'].get('avg_speed_ms', 0)
        stroke_rate = w['metrics'].get('avg_stroke_rate', 0)
        grade = w['grade']
        score = w['total_score']
        wtype = w['workout_type']
        
        table_data.append([
            f"#{i+1}",
            date_str,
            f"{distance:.0f}m",
            f"{time_min:.0f}min",
            format_speed(speed),
            f"{stroke_rate:.0f}",
            wtype,
            grade,
            f"{score:.0f}"
        ])
    
    # Create table
    headers = ['#', 'Date', 'Distance', 'Time', 'Pace', 'SR', 'Type', 'Grade', 'Score']
    table = ax_table.table(cellText=table_data, colLabels=headers,
                          cellLoc='center', loc='center',
                          bbox=[0, 0, 1, 1])
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)
    
    # Style header row
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#4a90e2')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Style grade cells
    for i, w in enumerate(workouts):
        grade = w['grade']
        grade_color = colors.get(grade, 'white')
        table[(i+1, 7)].set_facecolor(grade_color)
        table[(i+1, 7)].set_text_props(weight='bold', color='white')
    
    # Style score cells based on grade
    for i, w in enumerate(workouts):
        score = w['total_score']
        if score >= 85:
            bg_color = 'lightgreen'
        elif score >= 70:
            bg_color = 'lightblue'
        elif score >= 55:
            bg_color = 'lightyellow'
        else:
            bg_color = 'lightcoral'
        table[(i+1, 8)].set_facecolor(bg_color)
    
    ax_table.set_title('Workout Summary Table', fontsize=12, fontweight='bold', pad=20)
    
    # Save
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ Multi-workout dashboard saved to: {output_file}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Generate multi-workout swimming dashboard')
    parser.add_argument('swimming_folder', nargs='?', default='csv_folder/swimming',
                       help='Path to swimming CSV folder (default: csv_folder/swimming)')
    parser.add_argument('-n', '--num-workouts', type=int, default=10,
                       help='Number of recent workouts to analyze (default: 10)')
    parser.add_argument('-o', '--output', help='Output file path (default: swim_multi_dashboard.png)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.swimming_folder):
        print(f"❌ Error: Folder not found: {args.swimming_folder}")
        sys.exit(1)
    
    print(f"🔍 Finding {args.num_workouts} most recent swimming workouts...")
    csv_files = get_recent_swim_files(args.swimming_folder, args.num_workouts)
    
    if len(csv_files) == 0:
        print(f"❌ No CSV files found in {args.swimming_folder}")
        sys.exit(1)
    
    print(f"📊 Analyzing {len(csv_files)} workouts...")
    workouts = analyze_all_workouts(csv_files)
    
    if len(workouts) == 0:
        print("❌ No workouts could be analyzed")
        sys.exit(1)
    
    if args.output:
        output_file = args.output
    else:
        output_file = "swim_multi_dashboard.png"
    
    generate_multi_dashboard(workouts, output_file)
    print(f"✅ Dashboard complete! Analyzed {len(workouts)} workouts.")


if __name__ == "__main__":
    main()
