# Swimming Workout Dashboard - FastAPI Application

A full-stack web application for analyzing swimming workouts with automated scoring, visualization, and coaching recommendations.

## Features

- 📊 **Upload CSV workout files** from Coros devices
- 🎯 **Automated scoring** (A/B/C/D grades) based on 4 key metrics
- 📈 **Interactive visualizations**:
  - Speed & Stroke Rate trends over time
  - Speed vs Efficiency cloud plot (new!)
- ✅ **Pros & Cons** analysis
- 📋 **Next workout prescriptions** based on limiters
- 🔄 **Workout comparison** - Compare multiple workouts to track progress
- 🎨 **Modern, responsive UI**

## Installation

1. Navigate to the dashboard directory:
```bash
cd fastapi_dashboard
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the FastAPI server:
```bash
cd backend
python main.py
```

Or using uvicorn directly:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

2. Open your browser and navigate to:
```
http://localhost:8000
```

## Usage

1. **Upload a CSV file**: Click "Choose File" or drag and drop a swimming workout CSV file
2. **View Analysis**: The dashboard will automatically:
   - Calculate scores (Distance, Pace, Stroke, Speed Gears)
   - Assign a grade (A/B/C/D)
   - Generate pros and cons
   - Provide next workout prescription
   - Display interactive charts

## API Endpoints

### `GET /`
Main dashboard page (HTML)

### `POST /api/analyze`
Analyze uploaded CSV file

**Request**: Multipart form data with `file` field (CSV file)

**Response**: JSON with analysis results:
```json
{
  "metadata": {...},
  "metrics": {...},
  "workout_type": "Endurance",
  "grade": "B",
  "sub_scores": {...},
  "total_score": 75,
  "verdict": "...",
  "pros": [...],
  "cons": [...],
  "prescription": {...}
}
```

### `GET /api/health`
Health check endpoint

## Project Structure

```
fastapi_dashboard/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── analysis_engine.py      # Workout analysis logic
│   └── comparison_engine.py   # Multi-workout comparison
├── templates/
│   └── index.html              # Frontend HTML with Chart.js
├── static/                     # Static files (if needed)
├── uploads/                     # Temporary file storage
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── QUICKSTART.md                # Quick setup guide
├── COMPARISON_FEATURE.md        # Comparison feature docs
└── TROUBLESHOOTING.md           # Troubleshooting guide
```

## Development

The application uses:
- **FastAPI** for the backend API
- **Pandas** for data processing
- **Chart.js** for visualizations
- **Jinja2** for templating

## Notes

- Uploaded files are temporarily stored and automatically deleted after analysis
- The application expects CSV files with Coros workout data format
- All analysis happens server-side for security
