#!/usr/bin/env python3
"""
Analyze Coros FIT files and generate Strava-style comments and workout suggestions.
"""

import os
import glob
from datetime import datetime
from fitparse import FitFile
import pandas as pd
from typing import List, Dict, Optional
import json


def parse_fit_file(file_path: str) -> Optional[Dict]:
    """Parse a FIT file and extract workout data."""
    try:
        fitfile = FitFile(file_path)
        
        # Initialize data dictionary
        workout_data = {
            'file': os.path.basename(file_path),
            'timestamp': None,
            'sport': None,
            'total_distance': 0.0,  # meters
            'total_time': 0.0,  # seconds
            'avg_pace': None,  # seconds per km
            'max_pace': None,
            'avg_heart_rate': None,
            'max_heart_rate': None,
            'avg_cadence': None,
            'total_elevation_gain': 0.0,  # meters
            'calories': 0,
            'temperature': None,
            'records': []
        }
        
        # Parse messages
        for record in fitfile.get_messages('file_id'):
            for field in record:
                if field.name == 'time_created':
                    workout_data['timestamp'] = field.value
        
        for record in fitfile.get_messages('sport'):
            for field in record:
                if field.name == 'sport':
                    workout_data['sport'] = field.value
        
        # Parse session data
        for record in fitfile.get_messages('session'):
            for field in record:
                if field.name == 'total_distance':
                    workout_data['total_distance'] = field.value or 0.0
                elif field.name == 'total_elapsed_time':
                    workout_data['total_time'] = field.value or 0.0
                elif field.name == 'avg_heart_rate':
                    workout_data['avg_heart_rate'] = field.value
                elif field.name == 'max_heart_rate':
                    workout_data['max_heart_rate'] = field.value
                elif field.name == 'total_ascent':
                    workout_data['total_elevation_gain'] = field.value or 0.0
                elif field.name == 'total_calories':
                    workout_data['calories'] = field.value or 0
                elif field.name == 'avg_cadence':
                    workout_data['avg_cadence'] = field.value
        
        # Parse record data for detailed analysis
        records = []
        for record in fitfile.get_messages('record'):
            record_data = {}
            for field in record:
                if field.name == 'distance':
                    record_data['distance'] = field.value
                elif field.name == 'speed':
                    record_data['speed'] = field.value  # m/s
                elif field.name == 'heart_rate':
                    record_data['heart_rate'] = field.value
                elif field.name == 'cadence':
                    record_data['cadence'] = field.value
                elif field.name == 'altitude':
                    record_data['altitude'] = field.value
                elif field.name == 'timestamp':
                    record_data['timestamp'] = field.value
            if record_data:
                records.append(record_data)
        
        workout_data['records'] = records
        
        # Calculate pace from distance and time
        if workout_data['total_distance'] > 0 and workout_data['total_time'] > 0:
            # Convert to km and calculate pace in seconds per km
            distance_km = workout_data['total_distance'] / 1000.0
            time_minutes = workout_data['total_time'] / 60.0
            if distance_km > 0:
                workout_data['avg_pace'] = (workout_data['total_time'] / distance_km) / 60.0  # minutes per km
        
        # Calculate max pace from records
        if records:
            speeds = [r.get('speed', 0) for r in records if r.get('speed')]
            if speeds:
                max_speed = max(speeds)  # m/s
                if max_speed > 0:
                    workout_data['max_pace'] = (1000.0 / max_speed) / 60.0  # minutes per km
        
        return workout_data if workout_data['timestamp'] else None
        
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None


def estimate_max_heart_rate(age: Optional[int] = None) -> int:
    """Estimate max heart rate using age or default to 220 - age formula."""
    # Default to 190 if age unknown (typical for adults)
    if age is None:
        return 190
    return 220 - age


def get_heart_rate_zone(hr: int, max_hr: int) -> str:
    """Determine heart rate zone."""
    percentage = (hr / max_hr * 100) if max_hr > 0 else 0
    
    if percentage >= 90:
        return "Zone 5 (Maximum)"
    elif percentage >= 80:
        return "Zone 4 (Threshold)"
    elif percentage >= 70:
        return "Zone 3 (Aerobic)"
    elif percentage >= 60:
        return "Zone 2 (Easy)"
    else:
        return "Zone 1 (Recovery)"


def detect_activity_type(pace: Optional[float], sport: Optional[str]) -> str:
    """Detect if activity is running, walking, or other based on pace."""
    if sport:
        sport_lower = str(sport).lower()
        if 'run' in sport_lower:
            return 'running'
        elif 'walk' in sport_lower or 'hike' in sport_lower:
            return 'walking'
        elif 'bike' in sport_lower or 'cycling' in sport_lower:
            return 'cycling'
    
    if pace:
        if pace < 8.0:  # Faster than 8 min/km is likely running
            return 'running'
        elif pace > 12.0:  # Slower than 12 min/km is likely walking
            return 'walking'
        else:
            return 'running'  # Default to running for moderate paces
    
    return 'unknown'


def analyze_workout(workout: Dict) -> Dict:
    """Analyze a single workout and generate insights."""
    analysis = {
        'summary': '',
        'highlights': [],
        'suggestions': []
    }
    
    sport = workout.get('sport', 'unknown')
    distance_km = workout.get('total_distance', 0) / 1000.0
    time_minutes = workout.get('total_time', 0) / 60.0
    avg_pace = workout.get('avg_pace')
    avg_hr = workout.get('avg_heart_rate')
    max_hr = workout.get('max_heart_rate')
    elevation = workout.get('total_elevation_gain', 0)
    calories = workout.get('calories', 0)
    
    # Use estimated max HR for zone calculations (workout max_hr is just the max in that workout)
    estimated_max_hr = estimate_max_heart_rate()
    
    # Detect activity type
    activity_type = detect_activity_type(avg_pace, sport)
    
    # Generate summary
    summary_parts = []
    
    if activity_type != 'unknown':
        summary_parts.append(activity_type.capitalize())
    elif sport and sport != 'unknown':
        summary_parts.append(f"{sport.capitalize()}")
    
    if distance_km > 0:
        if distance_km < 1:
            summary_parts.append(f"{distance_km * 1000:.0f}m")
        else:
            summary_parts.append(f"{distance_km:.2f}km")
    
    if time_minutes > 0:
        hours = int(time_minutes // 60)
        minutes = int(time_minutes % 60)
        if hours > 0:
            summary_parts.append(f"{hours}h {minutes}m")
        else:
            summary_parts.append(f"{minutes}m")
    
    if avg_pace:
        pace_min = int(avg_pace)
        pace_sec = int((avg_pace - pace_min) * 60)
        summary_parts.append(f"avg pace {pace_min}:{pace_sec:02d}/km")
    
    analysis['summary'] = " • ".join(summary_parts)
    
    # Generate highlights
    if elevation > 100:
        analysis['highlights'].append(f"🏔️ {elevation:.0f}m elevation gain - great hill work!")
    
    if avg_hr:
        hr_zone = get_heart_rate_zone(avg_hr, estimated_max_hr)
        hr_percentage = (avg_hr / estimated_max_hr * 100) if estimated_max_hr > 0 else 0
        
        if hr_percentage >= 80:
            analysis['highlights'].append(f"💪 High intensity effort - {hr_zone} (avg HR: {avg_hr} bpm)")
        elif hr_percentage >= 70:
            analysis['highlights'].append(f"🔥 Moderate intensity - {hr_zone} (avg HR: {avg_hr} bpm)")
        elif hr_percentage >= 60:
            analysis['highlights'].append(f"🏃 Steady aerobic effort - {hr_zone} (avg HR: {avg_hr} bpm)")
        else:
            analysis['highlights'].append(f"🧘 Easy recovery pace - {hr_zone} (avg HR: {avg_hr} bpm)")
    
    if calories > 500:
        analysis['highlights'].append(f"🔥 {calories} calories burned")
    
    if activity_type == 'running':
        if distance_km > 10:
            analysis['highlights'].append(f"📏 Long distance run - well done!")
        elif distance_km > 5:
            analysis['highlights'].append(f"✅ Solid distance run")
    
    # Generate suggestions based on activity type
    if activity_type == 'running':
        if avg_pace:
            if avg_pace < 4.5:  # Very fast pace
                analysis['suggestions'].append("⚡ Consider adding recovery days after this intense effort")
                analysis['suggestions'].append("💡 Mix in some easy runs to build aerobic base")
            elif avg_pace < 6.0:  # Fast pace
                analysis['suggestions'].append("🎯 Great tempo effort! Consider adding intervals for speed work")
            elif avg_pace > 7.0:  # Easy pace
                analysis['suggestions'].append("💪 Good base building - try adding tempo runs (comfortably hard pace)")
        
        if elevation > 200:
            analysis['suggestions'].append("🏃 Include flat runs to work on speed and efficiency")
        
        if avg_hr:
            hr_percentage = (avg_hr / estimated_max_hr * 100) if estimated_max_hr > 0 else 0
            if hr_percentage >= 80:
                analysis['suggestions'].append("🔄 Next workout: Easy recovery run at 60-70% max HR")
            elif hr_percentage < 70:
                analysis['suggestions'].append("⚡ Next workout: Tempo run or intervals to build speed")
        
        if distance_km > 15:
            analysis['suggestions'].append("🎯 Consider shorter, faster runs to improve VO2 max")
        elif distance_km < 3 and avg_pace and avg_pace > 6.0:
            analysis['suggestions'].append("📈 Try extending your distance gradually for better endurance")
    
    elif activity_type == 'walking':
        analysis['suggestions'].append("🚶 Great for active recovery and building base fitness")
        if distance_km > 5:
            analysis['suggestions'].append("💪 Consider mixing in some running intervals to increase intensity")
    
    if not analysis['suggestions']:
        analysis['suggestions'].append("💪 Keep up the consistent training!")
        if activity_type == 'running':
            analysis['suggestions'].append("🎯 Mix in variety: intervals, tempo, and easy runs")
    
    return analysis


def generate_strava_comment(workout: Dict, analysis: Dict) -> str:
    """Generate a Strava-style comment for the workout."""
    comment_parts = []
    
    # Main summary
    comment_parts.append(f"📊 {analysis['summary']}")
    comment_parts.append("")
    
    # Highlights
    if analysis['highlights']:
        comment_parts.append("🌟 Highlights:")
        for highlight in analysis['highlights']:
            comment_parts.append(f"  {highlight}")
        comment_parts.append("")
    
    # Suggestions
    if analysis['suggestions']:
        comment_parts.append("💡 Suggestions for next workouts:")
        for suggestion in analysis['suggestions'][:3]:  # Limit to 3 suggestions
            comment_parts.append(f"  {suggestion}")
    
    return "\n".join(comment_parts)


def analyze_all_workouts(data_dir: str) -> List[Dict]:
    """Analyze all FIT files in the directory."""
    fit_files = glob.glob(os.path.join(data_dir, "*.fit"))
    fit_files.sort(key=os.path.getmtime, reverse=True)  # Most recent first
    
    print(f"Found {len(fit_files)} FIT files")
    print("=" * 80)
    
    all_workouts = []
    
    for fit_file in fit_files[:20]:  # Analyze last 20 workouts
        print(f"\nAnalyzing: {os.path.basename(fit_file)}")
        workout = parse_fit_file(fit_file)
        
        if workout:
            analysis = analyze_workout(workout)
            comment = generate_strava_comment(workout, analysis)
            
            workout_result = {
                'workout': workout,
                'analysis': analysis,
                'comment': comment
            }
            all_workouts.append(workout_result)
            
            print(comment)
            print("=" * 80)
    
    return all_workouts


def generate_training_recommendations(all_workouts: List[Dict]) -> str:
    """Generate overall training recommendations based on all workouts."""
    if not all_workouts:
        return "No workouts analyzed."
    
    # Aggregate statistics
    total_distance = sum(w['workout'].get('total_distance', 0) / 1000.0 for w in all_workouts)
    total_time = sum(w['workout'].get('total_time', 0) / 60.0 for w in all_workouts)
    avg_hrs = [w['workout'].get('avg_heart_rate') for w in all_workouts if w['workout'].get('avg_heart_rate')]
    avg_paces = [w['workout'].get('avg_pace') for w in all_workouts if w['workout'].get('avg_pace')]
    
    recommendations = []
    recommendations.append("🎯 OVERALL TRAINING RECOMMENDATIONS")
    recommendations.append("=" * 80)
    recommendations.append("")
    
    recommendations.append(f"📊 Recent Training Volume:")
    recommendations.append(f"  • Total Distance: {total_distance:.2f} km")
    recommendations.append(f"  • Total Time: {total_time/60:.1f} hours")
    recommendations.append(f"  • Workouts Analyzed: {len(all_workouts)}")
    recommendations.append("")
    
    if avg_hrs:
        avg_hr = sum(avg_hrs) / len(avg_hrs)
        estimated_max_hr = estimate_max_heart_rate()
        hr_percentage = (avg_hr / estimated_max_hr * 100) if estimated_max_hr > 0 else 0
        recommendations.append(f"💓 Average Heart Rate: {avg_hr:.0f} bpm ({hr_percentage:.0f}% of estimated max)")
        recommendations.append("")
    
    if avg_paces:
        avg_pace = sum(avg_paces) / len(avg_paces)
        pace_min = int(avg_pace)
        pace_sec = int((avg_pace - pace_min) * 60)
        recommendations.append(f"⚡ Average Pace: {pace_min}:{pace_sec:02d}/km")
        recommendations.append("")
    
    recommendations.append("💡 Training Suggestions:")
    recommendations.append("")
    
    # Analyze training patterns
    if avg_paces:
        avg_pace = sum(avg_paces) / len(avg_paces)
        if avg_pace < 5.0:
            recommendations.append("  ⚠️  Your recent workouts have been very intense!")
            recommendations.append("     → Add more easy/recovery runs (60-70% max HR)")
            recommendations.append("     → Follow the 80/20 rule: 80% easy, 20% hard")
        elif avg_pace > 6.0:
            recommendations.append("  🎯 Great base building! Time to add some intensity:")
            recommendations.append("     → Include 1-2 interval sessions per week")
            recommendations.append("     → Add tempo runs (comfortably hard pace)")
    
    recommendations.append("")
    recommendations.append("📅 Weekly Training Plan Suggestion:")
    recommendations.append("  • Monday: Easy run (60-70% max HR)")
    recommendations.append("  • Wednesday: Interval or tempo run")
    recommendations.append("  • Friday: Easy run or rest")
    recommendations.append("  • Sunday: Long run (70-80% max HR)")
    recommendations.append("")
    recommendations.append("💪 Remember: Consistency > Intensity")
    recommendations.append("   Recovery is just as important as training!")
    
    return "\n".join(recommendations)


if __name__ == "__main__":
    data_dir = "/Users/hongtang/Documents/coros_fit/corosfitdata"
    
    print("🏃 Analyzing Coros Workout Data")
    print("=" * 80)
    
    all_workouts = analyze_all_workouts(data_dir)
    
    if all_workouts:
        print("\n\n")
        recommendations = generate_training_recommendations(all_workouts)
        print(recommendations)
        
        # Save results to file
        output_file = "/Users/hongtang/Documents/coros_fit/workout_analysis.txt"
        with open(output_file, 'w') as f:
            f.write("COROS WORKOUT ANALYSIS\n")
            f.write("=" * 80 + "\n\n")
            for workout_result in all_workouts:
                f.write(workout_result['comment'])
                f.write("\n\n" + "=" * 80 + "\n\n")
            f.write("\n\n")
            f.write(recommendations)
        
        print(f"\n\n✅ Analysis saved to: {output_file}")
