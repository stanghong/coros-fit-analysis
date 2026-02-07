#!/usr/bin/env python3
"""
Create HR vs Pace plot for long runs to assess running economy.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from typing import List, Dict, Tuple
import glob


def get_long_run_files(running_folder: str, min_distance_km: float = 10.0, top_n: int = 5) -> List[str]:
    """Get the most recent long run CSV files."""
    csv_files = glob.glob(os.path.join(running_folder, "*.csv"))
    
    runs = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, nrows=1)
            
            distance = None
            if 'session_total_distance' in df.columns:
                distance = df['session_total_distance'].iloc[0]
            elif 'total_distance' in df.columns:
                distance = df['total_distance'].iloc[0]
            
            if distance is not None and pd.notna(distance):
                if distance > 100:
                    distance = distance / 1000.0
                elif distance < 0.1:
                    distance = None
            
            timestamp = None
            if 'session_start_time' in df.columns:
                timestamp = df['session_start_time'].iloc[0]
            elif 'timestamp' in df.columns:
                timestamp = df['timestamp'].iloc[0]
            
            if distance is not None and distance >= min_distance_km:
                runs.append({
                    'file': csv_file,
                    'distance': distance,
                    'timestamp': timestamp
                })
        except:
            continue
    
    runs.sort(key=lambda x: x['timestamp'] if x['timestamp'] else '', reverse=True)
    return [r['file'] for r in runs[:top_n]]


def extract_hr_pace_data(csv_file: str) -> Tuple[pd.Series, pd.Series, pd.Series, Dict]:
    """
    Extract HR, pace, and speed data from a CSV file.
    
    Returns:
        Tuple of (heart_rate, pace_min_per_km, speed_m_per_s, metadata)
    """
    df = pd.read_csv(csv_file)
    
    # Get metadata
    metadata = {}
    if 'session_total_distance' in df.columns:
        metadata['distance'] = df['session_total_distance'].iloc[0] / 1000.0
    if 'session_start_time' in df.columns:
        metadata['date'] = df['session_start_time'].iloc[0]
    metadata['filename'] = os.path.basename(csv_file)
    
    # Get heart rate
    hr_data = df['heart_rate'].dropna() if 'heart_rate' in df.columns else pd.Series()
    
    # Get speed and convert to pace
    speed_col = None
    for col in ['enhanced_speed', 'speed']:
        if col in df.columns:
            speed_col = col
            break
    
    if speed_col:
        speed_data = df[speed_col].dropna()
        # Convert speed (m/s) to pace (min/km)
        pace_data = (1000.0 / speed_data) / 60.0  # minutes per km
    else:
        speed_data = pd.Series()
        pace_data = pd.Series()
    
    # Align HR, pace, and speed data by index
    if len(hr_data) > 0 and len(pace_data) > 0:
        # Use the shorter length
        min_len = min(len(hr_data), len(pace_data))
        hr_data = hr_data.iloc[:min_len]
        pace_data = pace_data.iloc[:min_len]
        if len(speed_data) > 0:
            speed_data = speed_data.iloc[:min_len]
        
        # Filter out invalid data
        valid_mask = (hr_data > 0) & (hr_data < 220) & (pace_data > 0) & (pace_data < 30)
        if len(speed_data) > 0:
            valid_mask = valid_mask & (speed_data > 0) & (speed_data < 10)
        hr_data = hr_data[valid_mask]
        pace_data = pace_data[valid_mask]
        if len(speed_data) > 0:
            speed_data = speed_data[valid_mask]
    
    return hr_data, pace_data, speed_data, metadata


def calculate_economy_metrics(hr_data: pd.Series, pace_data: pd.Series, speed_data: pd.Series = None) -> Dict:
    """Calculate running economy metrics."""
    if len(hr_data) == 0 or len(pace_data) == 0:
        return {}
    
    # Calculate HR per speed (lower is better - more economical)
    # This is the slope of HR vs Speed relationship
    if len(hr_data) > 10:
        # Use speed if available, otherwise convert from pace
        if speed_data is not None and len(speed_data) > 0:
            # Align speed with HR
            min_len = min(len(hr_data), len(speed_data))
            hr_aligned = hr_data.iloc[:min_len]
            speed_aligned = speed_data.iloc[:min_len]
            
            # Filter valid data
            valid_mask = (hr_aligned > 0) & (hr_aligned < 220) & (speed_aligned > 0) & (speed_aligned < 10)
            hr_valid = hr_aligned[valid_mask]
            speed_valid = speed_aligned[valid_mask]
            
            if len(hr_valid) > 10:
                # HR vs Speed: positive slope = HR increases with speed (expected)
                # Lower slope = more economical (HR doesn't spike as much)
                z = np.polyfit(speed_valid.values, hr_valid.values, 1)
                speed_slope = z[0]  # HR increase per m/s
                intercept = z[1]
                correlation = np.corrcoef(speed_valid.values, hr_valid.values)[0, 1]
        else:
            # Convert pace to speed for analysis
            speed_from_pace = 1000.0 / (pace_data * 60.0)  # m/s
            min_len = min(len(hr_data), len(speed_from_pace))
            hr_aligned = hr_data.iloc[:min_len]
            speed_aligned = speed_from_pace.iloc[:min_len]
            
            valid_mask = (hr_aligned > 0) & (hr_aligned < 220) & (speed_aligned > 0) & (speed_aligned < 10)
            hr_valid = hr_aligned[valid_mask]
            speed_valid = speed_aligned[valid_mask]
            
            if len(hr_valid) > 10:
                z = np.polyfit(speed_valid.values, hr_valid.values, 1)
                speed_slope = z[0]
                intercept = z[1]
                correlation = np.corrcoef(speed_valid.values, hr_valid.values)[0, 1]
            else:
                speed_slope = None
                intercept = None
                correlation = None
        
        # Also calculate HR vs Pace for display
        z_pace = np.polyfit(pace_data.values, hr_data.values, 1)
        pace_slope = z_pace[0]  # HR change per min/km (negative = HR decreases as pace slows)
        pace_correlation = np.corrcoef(pace_data.values, hr_data.values)[0, 1]
        
        # Average HR at different pace zones
        pace_zones = {
            'easy': pace_data.quantile(0.75),  # Slowest 25% (higher pace = slower)
            'moderate': pace_data.median(),
            'hard': pace_data.quantile(0.25)  # Fastest 25% (lower pace = faster)
        }
        
        hr_at_zones = {}
        for zone, pace_threshold in pace_zones.items():
            if zone == 'easy':
                mask = pace_data >= pace_threshold
            elif zone == 'hard':
                mask = pace_data <= pace_threshold
            else:
                mask = (pace_data >= pace_threshold * 0.95) & (pace_data <= pace_threshold * 1.05)
            
            if mask.sum() > 0:
                hr_at_zones[zone] = hr_data[mask].mean()
        
        return {
            'speed_slope': speed_slope if 'speed_slope' in locals() else None,  # bpm per m/s (lower is better)
            'pace_slope': pace_slope,  # bpm per min/km
            'intercept': intercept if 'intercept' in locals() else None,
            'correlation': correlation if 'correlation' in locals() else pace_correlation,
            'hr_at_zones': hr_at_zones,
            'avg_hr': hr_data.mean(),
            'avg_pace': pace_data.mean()
        }
    
    return {}


def create_hr_vs_pace_plot(run_files: List[str], output_file: str) -> None:
    """Create HR vs Pace plot for all runs."""
    fig, ax = plt.subplots(figsize=(14, 10))
    
    colors = cm.viridis(np.linspace(0, 1, len(run_files)))
    
    all_metrics = []
    
    for i, csv_file in enumerate(run_files):
        hr_data, pace_data, speed_data, metadata = extract_hr_pace_data(csv_file)
        
        if len(hr_data) == 0 or len(pace_data) == 0:
            print(f"⚠ Skipping {metadata['filename']}: No valid HR/pace data")
            continue
        
        # Calculate metrics
        metrics = calculate_economy_metrics(hr_data, pace_data, speed_data)
        all_metrics.append({
            'file': metadata['filename'],
            'distance': metadata.get('distance', 0),
            'date': metadata.get('date', ''),
            'metrics': metrics
        })
        
        # Plot scatter with color gradient (time-based)
        scatter = ax.scatter(
            pace_data.values,
            hr_data.values,
            c=range(len(pace_data)),
            cmap='viridis',
            alpha=0.4,
            s=20,
            label=f"{metadata.get('distance', 0):.1f}km - {metadata.get('date', '')[:10]}",
            edgecolors='none'
        )
        
        # Plot trend line if we have enough data
        if metrics and ('speed_slope' in metrics or 'pace_slope' in metrics):
            pace_range = np.linspace(pace_data.min(), pace_data.max(), 100)
            slope = metrics.get('speed_slope') or metrics.get('pace_slope', 0)
            intercept = metrics.get('intercept', 0)
            hr_trend = slope * pace_range + intercept
            ax.plot(pace_range, hr_trend, '--', color=colors[i], linewidth=2, alpha=0.7)
    
    # Customize plot
    ax.set_xlabel('Pace (min/km)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Heart Rate (bpm)', fontsize=14, fontweight='bold')
    ax.set_title('HR vs Pace: Running Economy Analysis\n"Train to run cheap, not just fast"', 
                 fontsize=16, fontweight='bold', pad=20)
    
    # Invert x-axis so faster pace (lower min/km) is on the right
    ax.invert_xaxis()
    
    # Add grid
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add legend
    ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
    
    # Add text annotations for economy interpretation
    ax.text(0.02, 0.98, 
            'Economical Runner:\n• Lower HR at same pace\n• Steeper HR increase = less economical\n• Flatter slope = more economical',
            transform=ax.transAxes,
            fontsize=11,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
            family='monospace')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Plot saved to: {output_file}")
    
    # Print economy analysis
    print("\n" + "=" * 80)
    print("📊 RUNNING ECONOMY ANALYSIS")
    print("=" * 80)
    print("\nKodiak Rule: You don't train to run fast — you train to run cheap.")
    print("\nEconomy Metrics (HR increase per min/km pace):")
    print("-" * 80)
    
    for run_info in all_metrics:
        if run_info['metrics']:
            metrics = run_info['metrics']
            
            # Use speed slope if available (better indicator), otherwise use pace slope
            if metrics.get('speed_slope') is not None:
                slope = metrics['speed_slope']
                slope_type = "HR/Speed"
                slope_unit = "bpm per m/s"
                
                # Interpret economy based on speed slope
                # Lower slope = more economical (HR doesn't spike as much with speed)
                if slope < 8:
                    economy_status = "🟢 EXCELLENT - Very economical"
                elif slope < 12:
                    economy_status = "🟡 GOOD - Economical"
                elif slope < 18:
                    economy_status = "🟠 MODERATE - Room for improvement"
                else:
                    economy_status = "🔴 POOR - Not economical (strong for short efforts only)"
            else:
                slope = metrics.get('pace_slope', 0)
                slope_type = "HR/Pace"
                slope_unit = "bpm per min/km"
                # For pace, we want to see how HR changes when pace gets faster
                # Negative slope means HR decreases as pace slows (expected)
                # We want to see small changes
                abs_slope = abs(slope)
                if abs_slope < 5:
                    economy_status = "🟢 EXCELLENT - Very economical"
                elif abs_slope < 10:
                    economy_status = "🟡 GOOD - Economical"
                elif abs_slope < 15:
                    economy_status = "🟠 MODERATE - Room for improvement"
                else:
                    economy_status = "🔴 POOR - Not economical (strong for short efforts only)"
            
            correlation = metrics.get('correlation', 0)
            
            print(f"\n{run_info['file']}")
            print(f"  Distance: {run_info['distance']:.2f} km")
            print(f"  {slope_type} Slope: {slope:.1f} {slope_unit}")
            print(f"  Correlation: {correlation:.2f}")
            print(f"  Status: {economy_status}")
            
            if 'hr_at_zones' in metrics:
                zones = metrics['hr_at_zones']
                if 'easy' in zones and 'hard' in zones:
                    hr_diff = zones['hard'] - zones['easy']
                    print(f"  HR Range (Easy→Hard): {zones['easy']:.0f} → {zones['hard']:.0f} bpm (Δ{hr_diff:+.0f} bpm)")
    
    print("\n" + "=" * 80)
    print("💡 Interpretation:")
    print("  • Lower slope = More economical (HR doesn't spike as much with pace)")
    print("  • Higher slope = Less economical (HR spikes quickly = strong for short efforts)")
    print("  • Goal: Flatten the HR-Pace relationship through aerobic base training")
    print("=" * 80)


if __name__ == "__main__":
    running_folder = "/Users/hongtang/Documents/coros_fit/csv_folder/running"
    output_file = "/Users/hongtang/Documents/coros_fit/hr_vs_pace_analysis.png"
    
    print("🔍 Finding 5 most recent long runs...")
    long_run_files = get_long_run_files(running_folder, min_distance_km=10.0, top_n=5)
    
    if not long_run_files:
        print("No long runs found!")
        exit(1)
    
    print(f"Found {len(long_run_files)} long runs")
    print("Creating HR vs Pace plot...")
    
    create_hr_vs_pace_plot(long_run_files, output_file)
    
    print(f"\n✅ Analysis complete!")
