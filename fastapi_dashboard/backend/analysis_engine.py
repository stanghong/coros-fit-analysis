"""
Analysis engine for swimming workouts - extracted from dashboard generator.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


def load_swim_data(df: pd.DataFrame) -> Dict:
    """Load swimming workout data from DataFrame and extract metadata."""
    metadata = {}
    
    if len(df) == 0:
        return metadata
    
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
    
    return metadata


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
    
    # Detect speed gears (fast segments)
    if 'speed' in metrics and len(metrics['speed']) > 50:
        speed_arr = metrics['speed']
        avg_speed = np.mean(speed_arr)
        fast_threshold = avg_speed * 1.15
        fast_segments = speed_arr >= fast_threshold
        
        in_fast_segment = False
        fast_segment_count = 0
        fast_segment_length = 0
        
        for is_fast in fast_segments:
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
    
    # Calculate efficiency (speed per stroke rate - higher is better)
    if 'speed' in metrics and 'stroke_rate' in metrics:
        speed_arr = metrics['speed']
        stroke_arr = metrics['stroke_rate']
        min_len = min(len(speed_arr), len(stroke_arr))
        
        if min_len > 0:
            speed_aligned = speed_arr[:min_len]
            stroke_aligned = stroke_arr[:min_len]
            valid_mask = (speed_aligned > 0) & (stroke_aligned > 0)
            speed_valid = speed_aligned[valid_mask]
            stroke_valid = stroke_aligned[valid_mask]
            
            if len(speed_valid) > 0:
                efficiency = speed_valid / stroke_valid
                metrics['efficiency'] = efficiency
                metrics['efficiency_avg'] = np.mean(efficiency)
                metrics['efficiency_std'] = np.std(efficiency)
                metrics['efficiency_data'] = efficiency
                metrics['speed_for_efficiency'] = speed_valid
                metrics['stroke_rate_for_efficiency'] = stroke_valid
    
    return metrics


def detect_workout_type(df: pd.DataFrame, metrics: Dict) -> str:
    """Detect workout type: Endurance / Threshold / Speed / Recovery / Technique"""
    if 'speed' not in metrics or len(metrics.get('speed', [])) < 50:
        return "Recovery"
    
    speed_cv = metrics.get('speed_cv', 0)
    avg_speed = metrics.get('speed_avg', 0)
    
    if speed_cv > 15 and metrics.get('speed_gear_count', 0) > 3:
        return "Speed"
    
    if avg_speed > 0.8 and speed_cv < 10:
        if metrics.get('stop_percentage', 100) < 10:
            return "Threshold"
    
    if metrics.get('stop_percentage', 0) > 20:
        return "Technique"
    
    if speed_cv < 8 and metrics.get('stop_percentage', 100) < 15:
        return "Endurance"
    
    if avg_speed < 0.6:
        return "Recovery"
    
    return "Endurance"


def score_swim_workout(metrics: Dict, workout_type: str) -> Tuple[str, Dict, int]:
    """Score swimming workout (A/B/C/D) and return sub-scores."""
    sub_scores = {}
    
    # A) Distance Endurance (0-25)
    distance_score = 0
    distance_m = metrics.get('distance_m', 0)
    if distance_m > 0:
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
    
    if stop_pct > 20:
        pace_score = max(0, pace_score - 5)
    
    sub_scores['pace_consistency'] = pace_score
    
    # C) Stroke Rate & Stability (0-25)
    stroke_score = 0
    stroke_cv = metrics.get('stroke_rate_cv', 100)
    stroke_drop = abs(metrics.get('stroke_rate_drop', 0))
    
    if stroke_cv < 5:
        stroke_score = 15
    elif stroke_cv < 10:
        stroke_score = 12
    elif stroke_cv < 15:
        stroke_score = 8
    else:
        stroke_score = 5
    
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
    gear_count = metrics.get('speed_gear_count', 0)
    
    if gear_count >= 5:
        speed_gear_score = 25
    elif gear_count >= 3:
        speed_gear_score = 20
    elif gear_count >= 1:
        speed_gear_score = 15
    elif metrics.get('has_speed_gears', False):
        speed_gear_score = 10
    else:
        if workout_type == "Endurance":
            speed_gear_score = 15
        else:
            speed_gear_score = 5
    
    sub_scores['speed_gears'] = speed_gear_score
    
    total_score = sum(sub_scores.values())
    
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
    
    if len(pros) < 3:
        if metrics.get('distance_m', 0) > 1500:
            pros.append("Strong distance covered — building aerobic capacity")
        if metrics.get('stroke_rate_cv', 100) < 10:
            pros.append("Stable stroke rate — consistent technique")
    
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
    
    if len(cons) < 3:
        if metrics.get('speed_cv', 0) > 12:
            cons.append("Speed variability too high — structure your sets")
        if metrics.get('stroke_rate_cv', 100) > 15:
            cons.append("Stroke rate inconsistent — focus on rhythm")
    
    while len(pros) < 3:
        pros.append("Good effort — keep building consistency")
    while len(cons) < 3:
        cons.append("Room for improvement — focus on fundamentals")
    
    return pros[:3], cons[:3]


def prescribe_next_workout(grade: str, sub_scores: Dict, workout_type: str, metrics: Dict) -> Dict:
    """Prescribe the next workout based on current state."""
    min_score_key = min(sub_scores, key=sub_scores.get)
    prescription = {}
    
    if min_score_key == 'speed_gears' or (workout_type == "Endurance" and not metrics.get('has_speed_gears', False)):
        prescription['main_set'] = "12×100 @ moderate-hard, 20s rest\nCue: Hold stroke rate 34-36 spm, no over-glide"
        prescription['key_focus'] = "Speed gear development"
        prescription['drill_set'] = "8×25 fast (easy back) — focus on turnover"
    elif min_score_key == 'pace_consistency':
        prescription['main_set'] = "6×200 @ controlled pace, 30s rest\nRule: Rep 1 must feel 'too easy'\nCue: Even splits > fast rep 1"
        prescription['key_focus'] = "Pacing control"
        prescription['drill_set'] = "4×50 build (easy to fast) — feel the pace change"
    elif min_score_key == 'stroke_stability':
        prescription['main_set'] = "10×100 @ steady, 15s rest\nCue: Count strokes per length, maintain rhythm"
        prescription['key_focus'] = "Stroke rate consistency"
        prescription['drill_set'] = "6×50 with stroke count focus — efficiency over speed"
    elif min_score_key == 'distance_endurance':
        prescription['main_set'] = "3×500 continuous @ easy-moderate, 1 min rest\nCue: Build volume, maintain form"
        prescription['key_focus'] = "Aerobic base building"
        prescription['drill_set'] = "200 easy with focus on breathing rhythm"
    else:
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


def convert_to_native_types(obj):
    """Convert NumPy/pandas types to native Python types for JSON serialization."""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Series):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_native_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_native_types(item) for item in obj]
    elif pd.isna(obj):
        return None
    else:
        return obj


def analyze_workout(df: pd.DataFrame) -> Dict:
    """Complete analysis pipeline for a single workout."""
    metadata = load_swim_data(df)
    metrics = calculate_swim_metrics(df)
    workout_type = detect_workout_type(df, metrics)
    
    # Add distance to metrics
    metrics['distance_m'] = metadata.get('distance_m', 0)
    
    # Score workout
    grade, sub_scores, total_score = score_swim_workout(metrics, workout_type)
    verdict = generate_verdict(grade, sub_scores, workout_type, metrics)
    pros, cons = generate_pros_cons(metrics, sub_scores, workout_type)
    prescription = prescribe_next_workout(grade, sub_scores, workout_type, metrics)
    
    # Prepare result with all data
    result = {
        'metadata': metadata,
        'metrics': {
            'distance_m': metrics.get('distance_m', 0),
            'total_time_sec': metadata.get('total_time_sec', 0),
            'avg_speed_ms': metadata.get('avg_speed_ms', 0),
            'avg_stroke_rate': metadata.get('avg_stroke_rate', 0),
            'speed_cv': metrics.get('speed_cv', 0),
            'stop_percentage': metrics.get('stop_percentage', 0),
            'stroke_rate_cv': metrics.get('stroke_rate_cv', 0),
            'stroke_rate_drop': metrics.get('stroke_rate_drop', 0),
            'speed_gear_count': metrics.get('speed_gear_count', 0),
            'has_speed_gears': metrics.get('has_speed_gears', False),
            'speed_data': metrics.get('speed', []).tolist() if 'speed' in metrics and len(metrics.get('speed', [])) > 0 else [],
            'stroke_rate_data': metrics.get('stroke_rate', []).tolist() if 'stroke_rate' in metrics and len(metrics.get('stroke_rate', [])) > 0 else [],
            'efficiency_avg': metrics.get('efficiency_avg', 0),
            'efficiency_data': metrics.get('efficiency_data', []).tolist() if 'efficiency_data' in metrics and len(metrics.get('efficiency_data', [])) > 0 else [],
            'speed_for_efficiency': metrics.get('speed_for_efficiency', []).tolist() if 'speed_for_efficiency' in metrics and len(metrics.get('speed_for_efficiency', [])) > 0 else [],
            'stroke_rate_for_efficiency': metrics.get('stroke_rate_for_efficiency', []).tolist() if 'stroke_rate_for_efficiency' in metrics and len(metrics.get('stroke_rate_for_efficiency', [])) > 0 else [],
        },
        'workout_type': workout_type,
        'grade': grade,
        'sub_scores': sub_scores,
        'total_score': total_score,
        'verdict': verdict,
        'pros': pros,
        'cons': cons,
        'prescription': prescription
    }
    
    # Convert all NumPy/pandas types to native Python types
    return convert_to_native_types(result)