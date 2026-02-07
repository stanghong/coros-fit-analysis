# Multi-Workout Comparison Feature

## Overview
The comparison feature allows you to upload 2-20 swimming workout CSV files and get comprehensive analysis across all workouts with coach-like insights and recommendations.

## Features

### 1. Time Series Analysis
- **Score Trend**: Track overall performance scores over time
- **Distance Trend**: Monitor volume progression
- **Speed Trend**: Analyze speed improvements/declines
- **Sub-Scores Comparison**: Compare all 4 sub-scores (Distance, Pace, Stroke, Speed Gears) across workouts

### 2. Coach Insights
The system provides intelligent insights with reasoning:

**Performance Trends**:
- Detects improving/declining performance
- Identifies consistency vs variability
- Flags fatigue or overreaching

**Area-Specific Insights**:
- Identifies strongest and weakest areas
- Explains why each area is strong/weak
- Provides context for improvements

### 3. Strengths & Weaknesses Analysis
- **Strengths**: Areas consistently scoring above average
- **Weaknesses**: Areas consistently scoring below average
- Each includes:
  - Average score
  - Detailed reasoning
  - Why it matters for performance

### 4. Training Recommendations
Prioritized recommendations based on:
- **High Priority**: Address weakest limiter
- **Medium Priority**: Build on strengths
- **Low Priority**: Overall progression guidance

Each recommendation includes:
- Specific workout prescription
- Reasoning (why this workout)
- Frequency (how often)
- Key focus area

## How to Use

1. **Navigate to "Compare Workouts" tab**
2. **Upload 2-20 CSV files** (drag & drop or file picker)
3. **View comprehensive analysis**:
   - Time series charts
   - Coach insights with reasoning
   - Strengths & weaknesses
   - Training recommendations

## API Endpoint

### `POST /api/compare`

**Request**: Multipart form data with multiple `files` (CSV files)

**Response**: JSON with:
```json
{
  "workouts": [...],           // Individual workout analyses
  "time_series": {...},        // Time series data for charts
  "trends": {...},             // Calculated trends
  "insights": [...],           // Coach insights with reasoning
  "strengths_weaknesses": {...}, // Strengths and weaknesses
  "recommendations": [...],     // Training recommendations
  "summary": {...}             // Overall summary
}
```

## Coach Logic

### Trend Detection
- Compares first half vs second half of workouts
- Calculates percentage change
- Identifies improving/declining/stable trends

### Insight Generation
- **Positive**: Performance improving, strengths identified
- **Warning**: Performance declining, weaknesses flagged
- **Info**: Consistency observations, neutral insights

### Recommendation Priority
1. **High**: Address weakest limiter (biggest impact)
2. **Medium**: Build on strengths (leverage advantages)
3. **Low**: Overall progression (maintain momentum)

## Example Insights

**Performance Improving**:
> "Your overall scores are trending upward (15.2% improvement). This indicates you're adapting well to training."
> 
> **Reasoning**: Consistent improvement across multiple workouts suggests effective training stimulus and good recovery. Keep the momentum going!

**Area Needing Attention**:
> "Your Speed Gears has been declining. Focus training here."
> 
> **Reasoning**: Addressing this limiter will have the biggest impact on overall performance.

**Training Recommendation**:
> **Focus**: Speed Development
> **Workout**: 12×100 @ moderate-hard, 20s rest. Hold stroke rate 34-36 spm.
> **Reasoning**: You need more speed work to develop higher gears. Add controlled intensity.
> **Frequency**: 1-2x per week

## Technical Details

### Trend Calculation
- Splits workouts into first half and second half
- Calculates mean for each half
- Determines direction and percentage change
- Flags significant changes (>5%)

### Strength/Weakness Identification
- Calculates average sub-scores across all workouts
- Compares to overall average
- Identifies areas >3 points above/below average
- Provides specific reasoning for each

### Recommendation Engine
- Identifies lowest sub-score (limiter)
- Matches prescription to limiter type
- Considers overall trend (improving/declining)
- Provides specific workout with cues
