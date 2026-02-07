"""
Comparison engine for analyzing multiple swimming workouts over time.
Provides coach-like insights and reasoning.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from datetime import datetime
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from analysis_engine import analyze_workout


def analyze_multiple_workouts(workout_dataframes: List[pd.DataFrame]) -> Dict:
    """
    Analyze multiple workouts and provide comparison insights.
    
    Args:
        workout_dataframes: List of DataFrames, one per workout
        
    Returns:
        Dictionary with comparison analysis, trends, and coach insights
    """
    if len(workout_dataframes) == 0:
        return {"error": "No workouts provided"}
    
    # Analyze each workout
    workouts = []
    for i, df in enumerate(workout_dataframes):
        try:
            analysis = analyze_workout(df)
            analysis['workout_number'] = i + 1
            workouts.append(analysis)
        except Exception as e:
            continue
    
    if len(workouts) == 0:
        return {"error": "Could not analyze any workouts"}
    
    # Sort by date (most recent first)
    workouts.sort(key=lambda x: x.get('metadata', {}).get('date', ''), reverse=False)
    
    # Extract time series data
    time_series = extract_time_series(workouts)
    
    # Calculate trends
    trends = calculate_trends(workouts)
    
    # Generate coach insights
    insights = generate_coach_insights(workouts, trends)
    
    # Identify strengths and weaknesses
    strengths_weaknesses = identify_strengths_weaknesses(workouts, trends)
    
    # Training recommendations
    recommendations = generate_training_recommendations(workouts, trends, strengths_weaknesses)
    
    return {
        'workouts': workouts,
        'time_series': time_series,
        'trends': trends,
        'insights': insights,
        'strengths_weaknesses': strengths_weaknesses,
        'recommendations': recommendations,
        'summary': generate_summary(workouts, trends)
    }


def extract_time_series(workouts: List[Dict]) -> Dict:
    """Extract time series data for visualization."""
    dates = []
    distances = []
    times = []
    speeds = []
    stroke_rates = []
    scores = []
    grades = []
    sub_scores = {
        'distance_endurance': [],
        'pace_consistency': [],
        'stroke_stability': [],
        'speed_gears': []
    }
    
    for w in workouts:
        metadata = w.get('metadata', {})
        metrics = w.get('metrics', {})
        
        date_str = metadata.get('date', '')
        dates.append(date_str)
        distances.append(metrics.get('distance_m', 0))
        times.append(metrics.get('total_time_sec', 0))
        speeds.append(metrics.get('avg_speed_ms', 0))
        stroke_rates.append(metrics.get('avg_stroke_rate', 0))
        scores.append(w.get('total_score', 0))
        grades.append(w.get('grade', 'N/A'))
        
        sub_s = w.get('sub_scores', {})
        for key in sub_scores.keys():
            sub_scores[key].append(sub_s.get(key, 0))
    
    return {
        'dates': dates,
        'distances': distances,
        'times': times,
        'speeds': speeds,
        'stroke_rates': stroke_rates,
        'scores': scores,
        'grades': grades,
        'sub_scores': sub_scores
    }


def calculate_trends(workouts: List[Dict]) -> Dict:
    """Calculate trends across workouts."""
    if len(workouts) < 2:
        return {}
    
    time_series = extract_time_series(workouts)
    
    trends = {}
    
    # Distance trend
    distances = time_series['distances']
    if len(distances) >= 2:
        first_half = np.mean(distances[:len(distances)//2])
        second_half = np.mean(distances[len(distances)//2:])
        trends['distance'] = {
            'direction': 'improving' if second_half > first_half else 'declining',
            'change_pct': ((second_half - first_half) / first_half * 100) if first_half > 0 else 0,
            'avg': np.mean(distances),
            'trend': 'stable' if abs(second_half - first_half) / first_half < 0.05 else ('up' if second_half > first_half else 'down')
        }
    
    # Speed trend
    speeds = time_series['speeds']
    if len(speeds) >= 2:
        first_half = np.mean(speeds[:len(speeds)//2])
        second_half = np.mean(speeds[len(speeds)//2:])
        trends['speed'] = {
            'direction': 'improving' if second_half > first_half else 'declining',
            'change_pct': ((second_half - first_half) / first_half * 100) if first_half > 0 else 0,
            'avg': np.mean(speeds),
            'trend': 'stable' if abs(second_half - first_half) / first_half < 0.05 else ('up' if second_half > first_half else 'down')
        }
    
    # Score trend
    scores = time_series['scores']
    if len(scores) >= 2:
        first_half = np.mean(scores[:len(scores)//2])
        second_half = np.mean(scores[len(scores)//2:])
        trends['score'] = {
            'direction': 'improving' if second_half > first_half else 'declining',
            'change_pct': ((second_half - first_half) / first_half * 100) if first_half > 0 else 0,
            'avg': np.mean(scores),
            'trend': 'stable' if abs(second_half - first_half) / first_half < 0.05 else ('up' if second_half > first_half else 'down')
        }
    
    # Sub-score trends
    for key, values in time_series['sub_scores'].items():
        if len(values) >= 2:
            first_half = np.mean(values[:len(values)//2])
            second_half = np.mean(values[len(values)//2:])
            trends[f'sub_score_{key}'] = {
                'direction': 'improving' if second_half > first_half else 'declining',
                'change_pct': ((second_half - first_half) / first_half * 100) if first_half > 0 else 0,
                'avg': np.mean(values),
                'trend': 'stable' if abs(second_half - first_half) / first_half < 0.05 else ('up' if second_half > first_half else 'down')
            }
    
    return trends


def generate_coach_insights(workouts: List[Dict], trends: Dict) -> List[Dict]:
    """Generate coach-like insights with reasoning."""
    insights = []
    
    if len(workouts) < 2:
        return insights
    
    # Overall performance trend
    if 'score' in trends:
        score_trend = trends['score']
        if score_trend['trend'] == 'up':
            insights.append({
                'type': 'positive',
                'title': 'Performance Improving',
                'message': f"Your overall scores are trending upward ({score_trend['change_pct']:.1f}% improvement). This indicates you're adapting well to training.",
                'reasoning': 'Consistent improvement across multiple workouts suggests effective training stimulus and good recovery. Keep the momentum going!'
            })
        elif score_trend['trend'] == 'down':
            insights.append({
                'type': 'warning',
                'title': 'Performance Declining',
                'message': f"Your scores have declined by {abs(score_trend['change_pct']):.1f}%. This could indicate fatigue, overreaching, or need for recovery.",
                'reasoning': 'Declining performance over multiple sessions often signals accumulated fatigue. Consider a recovery week or deload.'
            })
    
    # Distance progression
    if 'distance' in trends:
        dist_trend = trends['distance']
        if dist_trend['trend'] == 'up' and dist_trend['change_pct'] > 10:
            insights.append({
                'type': 'positive',
                'title': 'Volume Building',
                'message': f"You're increasing training volume significantly ({dist_trend['change_pct']:.1f}%). Great for aerobic base development.",
                'reasoning': 'Progressive volume increase is key for endurance sports. Ensure you maintain form and allow adequate recovery between sessions.'
            })
    
    # Speed consistency
    if 'speed' in trends:
        speed_trend = trends['speed']
        if speed_trend['trend'] == 'stable':
            insights.append({
                'type': 'info',
                'title': 'Speed Consistency',
                'message': 'Your average speed is holding steady across workouts.',
                'reasoning': 'Stable speed with increasing volume suggests good aerobic efficiency. Consider adding speed work to develop higher gears.'
            })
        elif speed_trend['trend'] == 'up':
            insights.append({
                'type': 'positive',
                'title': 'Speed Improving',
                'message': f"Your average speed is increasing ({speed_trend['change_pct']:.1f}%). This indicates fitness gains.",
                'reasoning': 'Faster speeds at similar effort levels show improved fitness. This is a strong positive signal.'
            })
    
    # Sub-score analysis
    sub_score_trends = {k: v for k, v in trends.items() if k.startswith('sub_score_')}
    
    # Find strongest and weakest areas
    if sub_score_trends:
        improving = [k for k, v in sub_score_trends.items() if v['trend'] == 'up']
        declining = [k for k, v in sub_score_trends.items() if v['trend'] == 'down']
        
        if improving:
            best_area = improving[0].replace('sub_score_', '').replace('_', ' ').title()
            insights.append({
                'type': 'positive',
                'title': f'Strongest Area: {best_area}',
                'message': f'Your {best_area.lower()} is consistently improving across workouts.',
                'reasoning': f'This is your current strength. Use this as a foundation while working on other areas.'
            })
        
        if declining:
            weak_area = declining[0].replace('sub_score_', '').replace('_', ' ').title()
            insights.append({
                'type': 'warning',
                'title': f'Area Needing Attention: {weak_area}',
                'message': f'Your {weak_area.lower()} has been declining. Focus training here.',
                'reasoning': f'Addressing this limiter will have the biggest impact on overall performance.'
            })
    
    # Consistency check
    scores = [w.get('total_score', 0) for w in workouts]
    if len(scores) >= 3:
        score_cv = np.std(scores) / np.mean(scores) * 100 if np.mean(scores) > 0 else 0
        if score_cv < 10:
            insights.append({
                'type': 'positive',
                'title': 'Excellent Consistency',
                'message': 'Your performance is very consistent across workouts.',
                'reasoning': 'Low variability indicates good execution and appropriate training load. This is a sign of mature training.'
            })
        elif score_cv > 20:
            insights.append({
                'type': 'warning',
                'title': 'High Variability',
                'message': 'Your performance varies significantly between workouts.',
                'reasoning': 'High variability could indicate inconsistent effort, recovery issues, or training load fluctuations. Aim for more consistent execution.'
            })
    
    return insights


def identify_strengths_weaknesses(workouts: List[Dict], trends: Dict) -> Dict:
    """Identify consistent strengths and weaknesses."""
    if len(workouts) < 2:
        return {'strengths': [], 'weaknesses': []}
    
    # Calculate average sub-scores
    avg_sub_scores = {
        'distance_endurance': [],
        'pace_consistency': [],
        'stroke_stability': [],
        'speed_gears': []
    }
    
    for w in workouts:
        sub_s = w.get('sub_scores', {})
        for key in avg_sub_scores.keys():
            avg_sub_scores[key].append(sub_s.get(key, 0))
    
    # Calculate averages
    avg_scores = {k: np.mean(v) for k, v in avg_sub_scores.items()}
    
    # Identify strengths (above average)
    strengths = []
    weaknesses = []
    
    overall_avg = np.mean(list(avg_scores.values()))
    
    for key, value in avg_scores.items():
        name = key.replace('_', ' ').title()
        if value >= overall_avg + 3:  # Significantly above average
            strengths.append({
                'area': name,
                'score': value,
                'reasoning': get_strength_reasoning(key, value)
            })
        elif value <= overall_avg - 3:  # Significantly below average
            weaknesses.append({
                'area': name,
                'score': value,
                'reasoning': get_weakness_reasoning(key, value)
            })
    
    return {
        'strengths': strengths,
        'weaknesses': weaknesses,
        'average_scores': avg_scores
    }


def get_strength_reasoning(area: str, score: float) -> str:
    """Get reasoning for strength areas."""
    reasoning_map = {
        'distance_endurance': f"Your ability to sustain volume (score: {score:.1f}/25) shows strong aerobic base. You can handle longer sessions without breakdown.",
        'pace_consistency': f"Excellent pacing control (score: {score:.1f}/25) indicates good race execution skills. You maintain target speeds well.",
        'stroke_stability': f"Consistent stroke rate (score: {score:.1f}/25) shows good technique maintenance under fatigue. Your form holds up.",
        'speed_gears': f"Good speed variation (score: {score:.1f}/25) means you're using multiple intensity zones effectively in training."
    }
    return reasoning_map.get(area, f"Strong performance in this area (score: {score:.1f}/25).")


def get_weakness_reasoning(area: str, score: float) -> str:
    """Get reasoning for weakness areas."""
    reasoning_map = {
        'distance_endurance': f"Lower endurance scores (score: {score:.1f}/25) suggest you need to build volume gradually. Focus on continuous swimming.",
        'pace_consistency': f"Pacing variability (score: {score:.1f}/25) indicates you need more structured sets. Practice even splits.",
        'stroke_stability': f"Stroke rate instability (score: {score:.1f}/25) suggests technique breaks down. Add form-focused drills.",
        'speed_gears': f"Limited speed work (score: {score:.1f}/25) means you're missing high-intensity stimulus. Add fast intervals."
    }
    return reasoning_map.get(area, f"This area needs attention (score: {score:.1f}/25).")


def generate_training_recommendations(workouts: List[Dict], trends: Dict, strengths_weaknesses: Dict) -> List[Dict]:
    """Generate specific training recommendations based on analysis."""
    recommendations = []
    
    weaknesses = strengths_weaknesses.get('weaknesses', [])
    strengths = strengths_weaknesses.get('strengths', [])
    
    # Priority 1: Address weakest area
    if weaknesses:
        weakest = min(weaknesses, key=lambda x: x['score'])
        area = weakest['area'].lower()
        
        if 'distance' in area or 'endurance' in area:
            recommendations.append({
                'priority': 'High',
                'focus': 'Build Aerobic Base',
                'recommendation': '3×500 continuous @ easy-moderate, 1 min rest. Build volume gradually.',
                'reasoning': 'Your endurance is the limiter. Focus on continuous swimming to build aerobic capacity.',
                'frequency': '2-3x per week'
            })
        elif 'pace' in area or 'consistency' in area:
            recommendations.append({
                'priority': 'High',
                'focus': 'Pacing Control',
                'recommendation': '6×200 @ controlled pace, 30s rest. Rep 1 must feel "too easy".',
                'reasoning': 'Inconsistent pacing suggests you need more structured sets with specific pace targets.',
                'frequency': '1-2x per week'
            })
        elif 'stroke' in area or 'stability' in area:
            recommendations.append({
                'priority': 'High',
                'focus': 'Technique & Stroke Rate',
                'recommendation': '10×100 @ steady, 15s rest. Count strokes per length, maintain rhythm.',
                'reasoning': 'Stroke rate instability indicates technique breakdown. Focus on form over speed.',
                'frequency': '2x per week'
            })
        elif 'speed' in area or 'gear' in area:
            recommendations.append({
                'priority': 'High',
                'focus': 'Speed Development',
                'recommendation': '12×100 @ moderate-hard, 20s rest. Hold stroke rate 34-36 spm.',
                'reasoning': 'You need more speed work to develop higher gears. Add controlled intensity.',
                'frequency': '1-2x per week'
            })
    
    # Priority 2: Build on strengths
    if strengths:
        strongest = max(strengths, key=lambda x: x['score'])
        area = strongest['area'].lower()
        
        if 'distance' in area or 'endurance' in area:
            recommendations.append({
                'priority': 'Medium',
                'focus': 'Leverage Endurance Strength',
                'recommendation': 'Use your strong endurance base for longer threshold sets: 4×400 @ threshold, 45s rest.',
                'reasoning': 'Your endurance is a strength. Use it to build threshold fitness with longer intervals.',
                'frequency': '1x per week'
            })
    
    # Priority 3: Overall progression
    if 'score' in trends and trends['score']['trend'] == 'up':
        recommendations.append({
            'priority': 'Low',
            'focus': 'Maintain Momentum',
            'recommendation': 'Continue current training approach. Consider adding 5-10% volume or intensity.',
            'reasoning': 'You\'re improving consistently. Progressive overload will continue driving adaptation.',
            'frequency': 'Ongoing'
        })
    elif 'score' in trends and trends['score']['trend'] == 'down':
        recommendations.append({
            'priority': 'High',
            'focus': 'Recovery & Deload',
            'recommendation': 'Take a recovery week: reduce volume by 30-40%, focus on easy swimming.',
            'reasoning': 'Declining performance suggests accumulated fatigue. Recovery is essential for adaptation.',
            'frequency': 'This week'
        })
    
    return recommendations


def generate_summary(workouts: List[Dict], trends: Dict) -> Dict:
    """Generate overall summary."""
    if len(workouts) == 0:
        return {}
    
    total_distance = sum(w.get('metrics', {}).get('distance_m', 0) for w in workouts)
    avg_score = np.mean([w.get('total_score', 0) for w in workouts])
    grade_distribution = {}
    
    for w in workouts:
        grade = w.get('grade', 'N/A')
        grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
    
    most_common_grade = max(grade_distribution, key=grade_distribution.get) if grade_distribution else 'N/A'
    
    return {
        'total_workouts': len(workouts),
        'total_distance': total_distance,
        'average_score': avg_score,
        'most_common_grade': most_common_grade,
        'grade_distribution': grade_distribution,
        'overall_trend': trends.get('score', {}).get('trend', 'stable') if 'score' in trends else 'stable'
    }
