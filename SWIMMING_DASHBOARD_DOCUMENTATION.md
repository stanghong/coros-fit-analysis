# Swimming Dashboard: Implementation Strategy & Coaching Framework

## Overview
This document outlines the step-by-step approach used to create a comprehensive swimming workout dashboard with automated coaching feedback and next-workout prescriptions.

---

## 1. Data Loading & Preprocessing

### Strategy
- **Load CSV files** containing swimming workout data from Coros devices
- **Extract metadata** from session-level columns (first row typically contains summary data)
- **Process time-series data** from record-level columns (speed, cadence, heart rate over time)

### Key Data Fields Used
```python
# Session metadata (from first row)
- session_start_time: Workout date
- session_total_distance: Total distance in meters
- session_total_elapsed_time: Total time in seconds
- session_pool_length: Pool length (for context)
- session_avg_cadence: Average stroke rate (spm)
- session_avg_speed: Average speed (m/s)

# Time-series data (from all rows)
- enhanced_speed / speed: Speed in m/s (prefer enhanced_speed)
- cadence: Stroke rate in strokes per minute
- heart_rate: HR data (often unreliable in swimming)
- distance: Cumulative distance
```

### Implementation Details
- Filter out zero/negative values (representing stops or invalid data)
- Handle missing columns gracefully
- Convert units appropriately (m/s to pace, etc.)

---

## 2. Metric Calculation Framework

### A. Distance Endurance Metrics (0-25 points)
**Purpose**: Assess volume capacity and continuous swimming ability

**Calculations**:
1. **Total Distance Score**:
   - 2000m+ = 25 points (excellent)
   - 1500-2000m = 20 points (good)
   - 1000-1500m = 15 points (ok)
   - 500-1000m = 10 points (needs work)
   - <500m = 5 points (too short)

2. **Continuous Swimming Bonus**:
   - Stop percentage < 5% = +3 points
   - Stop percentage < 10% = +1 point
   - Stop percentage > 20% = penalty

**Stop Detection Logic**:
```python
stop_threshold = average_speed * 0.1  # Speed < 10% of average = stop
num_stops = count(speed < stop_threshold)
stop_percentage = (num_stops / total_samples) * 100
```

### B. Pace Consistency Metrics (0-25 points)
**Purpose**: Evaluate pacing control and speed variability

**Calculations**:
1. **Coefficient of Variation (CV)**:
   ```python
   CV = (std_dev(speed) / mean(speed)) * 100
   ```
   - CV < 3% = 25 points (excellent control)
   - CV 3-6% = 20 points (good)
   - CV 6-10% = 15 points (ok)
   - CV 10-15% = 10 points (needs work)
   - CV > 15% = 5 points (chaotic)

2. **Stop Penalty**:
   - Stop percentage > 20% = -5 points

**Why CV?**: Normalizes variability across different speed levels, making it comparable across workouts.

### C. Stroke Rate Stability (0-25 points)
**Purpose**: Assess technique consistency and form maintenance

**Calculations**:
1. **Stroke Rate CV**:
   - CV < 5% = 15 points
   - CV 5-10% = 12 points
   - CV 10-15% = 8 points
   - CV > 15% = 5 points

2. **Late-Run Drop Detection**:
   ```python
   first_20_percent = mean(stroke_rate[:len*0.2])
   last_20_percent = mean(stroke_rate[-len*0.2:])
   drop = first_20_percent - last_20_percent
   ```
   - Drop < 2 spm = +10 points (excellent)
   - Drop 2-4 spm = +5 points (good)
   - Drop > 5 spm = -5 points (fatigue breakdown)

**Why This Matters**: Stroke rate collapse indicates technique breakdown under fatigue, critical for long-distance performance.

### D. Speed Gear Presence (0-25 points)
**Purpose**: Detect whether athlete uses multiple intensity zones (not just one-gear endurance)

**Calculations**:
1. **Fast Segment Detection**:
   ```python
   fast_threshold = average_speed * 1.15  # 15% faster than average
   fast_segments = speed >= fast_threshold
   # Count continuous fast segments >= 20 seconds (20 data points)
   ```

2. **Scoring**:
   - 5+ fast segments = 25 points (excellent variation)
   - 3-4 segments = 20 points (good)
   - 1-2 segments = 15 points (some variation)
   - 0 segments (one-gear swim):
     - If workout_type == "Endurance": 15 points (acceptable)
     - Otherwise: 5 points (missing speed stimulus)

**Why This Matters**: One-gear endurance builds base but lacks speed development. Elite swimmers use multiple gears.

---

## 3. Workout Type Detection

### Strategy: Pattern Recognition Based on Metrics

**Endurance**:
- Speed CV < 8%
- Stop percentage < 15%
- Moderate average speed
- Low variability

**Threshold**:
- Average speed > 0.8 m/s
- Speed CV < 10%
- Stop percentage < 10%
- Sustained effort

**Speed**:
- Speed CV > 15%
- Multiple fast segments (speed_gear_count > 3)
- High variability pattern

**Technique**:
- Stop percentage > 20%
- Lower average speed
- Focus on form over pace

**Recovery**:
- Average speed < 0.6 m/s
- Low intensity

**Why Detection Matters**: Feedback must match intent. Criticizing an easy day for being "too slow" is counterproductive.

---

## 4. Scoring System (A/B/C/D)

### Grade Mapping
```python
Total Score = Distance (25) + Pace (25) + Stroke (25) + Speed Gears (25)

A: 85-100 points
   - Strong execution across all metrics
   - Minimal breakdown
   - Clear physiological signal

B: 70-84 points
   - Good session with 1-2 clear improvement areas
   - Most metrics solid, one limiter

C: 55-69 points
   - Session completed but poor structure/consistency
   - Wrong intensity or execution issues

D: <55 points
   - Unreliable data or major breakdown
   - Too many stops, extreme drift, or data quality issues
```

### Verdict Generation
**Strategy**: Identify the weakest sub-score and generate context-specific feedback

**Examples**:
- B grade + low speed_gears → "Strong aerobic base, speed gear missing"
- C grade + high stop_pct → "Too many interruptions — focus on continuous swimming"
- C grade + high speed_cv → "Pacing too chaotic — structure your sets better"

---

## 5. Pros & Cons Generation (Rule-Based)

### Strategy: Template-Based, Not Generic AI Fluff

**Pros Generation Rules**:
```python
if pace_consistency_score >= 20:
    → "Excellent pacing control — consistent speed throughout"

if distance_endurance_score >= 20:
    → "Solid endurance base — you sustained volume well"

if stroke_stability_score >= 20:
    → "Stroke rhythm held up under fatigue — good form"

if stop_percentage < 5:
    → "Minimal interruptions — great continuous swimming"

if speed_gears_score >= 20:
    → "Good speed variation — multiple gears used effectively"
```

**Cons Generation Rules**:
```python
if speed_gears_score < 15 and workout_type != "Recovery":
    → "One-gear swim — add speed gears for better stimulus"

if stop_percentage > 15:
    → "Too many interruptions — shorten rest, keep momentum"

if pace_consistency_score < 15:
    → "Pacing too variable — aim for more consistent splits"

if stroke_rate_drop > 4:
    → "Technique breaks late — add short form-focused repeats"
```

**Why Rule-Based?**: 
- Consistent, explainable feedback
- No hallucination or generic advice
- Athlete can understand why they got each point

---

## 6. Next Workout Prescription Engine

### Strategy: Identify Limiter → Prescribe Targeted Workout

### Step 1: Find the Weakest Area
```python
min_score_key = min(sub_scores, key=sub_scores.get)
min_score = sub_scores[min_score_key]
```

### Step 2: Match Prescription to Limiter

**If Speed Gears Missing**:
```
Main Set: 12×100 @ moderate-hard, 20s rest
Cue: Hold stroke rate 34-36 spm, no over-glide
Drill: 8×25 fast (easy back) — focus on turnover
Key Focus: Speed gear development
```

**If Pacing Issues**:
```
Main Set: 6×200 @ controlled pace, 30s rest
Rule: Rep 1 must feel "too easy"
Cue: Even splits > fast rep 1
Drill: 4×50 build (easy to fast) — feel the pace change
Key Focus: Pacing control
```

**If Stroke Rate Unstable**:
```
Main Set: 10×100 @ steady, 15s rest
Cue: Count strokes per length, maintain rhythm
Drill: 6×50 with stroke count focus — efficiency over speed
Key Focus: Stroke rate consistency
```

**If Distance/Endurance Low**:
```
Main Set: 3×500 continuous @ easy-moderate, 1 min rest
Cue: Build volume, maintain form
Drill: 200 easy with focus on breathing rhythm
Key Focus: Aerobic base building
```

### Step 3: Progression Logic
```python
if grade in ["A", "B"]:
    → Progress volume or intensity by 5-10%
    → Challenge with threshold or speed work

if grade in ["C", "D"]:
    → Repeat similar load or deload
    → Focus on fundamentals
```

---

## 7. Dashboard Visualization Strategy

### Single Workout Dashboard Layout

**Top Section (Header)**:
- Date, Sport, Workout Type
- Key metrics: Distance, Time, Pace, Variability, Stroke Rate
- Workout Goal tag

**Grade Section**:
- Large letter grade (color-coded)
- One-line verdict
- Total score

**Sub-Scores**:
- Horizontal bar chart
- 4 categories, each out of 25
- Color-coded for quick visual assessment

**Pros/Cons**:
- Side-by-side comparison
- 3 bullets each
- Color-coded boxes (green/red)

**Charts**:
- Speed vs Time (main performance chart)
- Stroke Rate vs Speed (efficiency map)

**Prescription Card**:
- Main set (specific workout)
- Key focus (one thing only)
- Drill set (technique component)

### Multi-Workout Dashboard Layout

**Overview Metrics**:
- Total distance across all workouts
- Total time
- Average score

**Trend Charts**:
1. Distance per workout (bar chart)
2. Scores over time (with grade thresholds)
3. Sub-scores comparison (grouped bars)
4. Speed trend (line chart)
5. Stroke rate trend (line chart)

**Distribution Charts**:
- Workout type pie chart
- Grade distribution bar chart

**Summary Table**:
- All workouts in one view
- Color-coded grades and scores
- Quick comparison across sessions

---

## 8. Key Coaching Principles Embedded

### Principle 1: Context Matters
- Workout type detection ensures feedback matches intent
- Easy days aren't criticized for being slow
- Speed days aren't criticized for variability

### Principle 2: One Thing at a Time
- Prescription focuses on ONE key limiter
- Prevents information overload
- Clear, actionable guidance

### Principle 3: Progression Logic
- A/B grades → progress
- C/D grades → repeat or deload
- Prevents overreaching

### Principle 4: Explainable Scoring
- Every point has a reason
- Athlete can see exactly what to improve
- No black-box AI decisions

### Principle 5: Specific Prescriptions
- Not "swim more" but "12×100 @ moderate-hard, 20s rest"
- Includes cues and drills
- Ready to execute

---

## 9. Technical Implementation Details

### Data Processing Pipeline
```
1. Load CSV → Extract metadata + time-series
2. Filter invalid data (zeros, outliers)
3. Calculate metrics (CV, drift, segments)
4. Detect workout type
5. Score workout (4 sub-scores → total)
6. Generate grade + verdict
7. Generate pros/cons (rule-based)
8. Prescribe next workout (limiter-based)
9. Visualize (matplotlib)
```

### Error Handling
- Missing columns → graceful degradation
- Empty data → default values
- Invalid calculations → fallback scores
- File errors → skip with warning

### Performance Considerations
- Process only necessary columns
- Vectorized operations (numpy/pandas)
- Efficient stop detection (vectorized comparisons)
- Fast segment detection (single pass algorithm)

---

## 10. Future Enhancements (Not Yet Implemented)

### Baseline Tracking
- Rolling 30-day averages
- Personal best markers
- Fitness trend analysis

### Comparative Analysis
- "vs last similar workout"
- "vs 30-day average"
- Progress indicators

### Advanced Metrics
- HR efficiency (when HR data reliable)
- Stroke length calculations
- Turn efficiency (if pool length known)
- Split analysis (if lap data available)

### Adaptive Prescriptions
- Learn from athlete responses
- Adjust difficulty based on completion rates
- Seasonal periodization

---

## Summary: Why This Approach Works

1. **Data-Driven**: Uses actual metrics, not assumptions
2. **Explainable**: Every score has a clear reason
3. **Actionable**: Prescriptions are specific and ready to execute
4. **Context-Aware**: Feedback matches workout intent
5. **Progressive**: Builds on strengths, addresses limiters
6. **Visual**: Easy to understand at a glance
7. **Scalable**: Can analyze single workouts or entire training blocks

The system acts as a **virtual coach** that:
- Analyzes performance objectively
- Identifies limiters systematically
- Prescribes targeted improvements
- Tracks progress over time

This creates a feedback loop: **Analyze → Identify → Prescribe → Execute → Repeat**
