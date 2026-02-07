# Coros Fit Data Analysis

A comprehensive workout analysis dashboard for Coros fitness device data, with focus on swimming workout analysis.

## Main Project: FastAPI Dashboard

The primary application is located in `fastapi_dashboard/`. This is a full-stack web application for analyzing swimming workouts.

### Quick Start

```bash
cd fastapi_dashboard
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd backend
python main.py
```

Then open http://localhost:8000 in your browser.

See [fastapi_dashboard/README.md](fastapi_dashboard/README.md) for detailed documentation.

## Features

- 📊 **Swimming Workout Analysis**: Upload CSV files and get automated scoring
- 🎯 **Grading System**: A/B/C/D grades based on multiple metrics
- 📈 **Interactive Visualizations**: Speed trends, stroke rate analysis, and efficiency cloud plots
- ✅ **Coaching Insights**: Pros/cons and next workout prescriptions
- 🔄 **Workout Comparison**: Compare multiple workouts to track progress

## Project Structure

```
.
├── fastapi_dashboard/          # Main web application
│   ├── backend/               # FastAPI backend
│   │   ├── main.py             # API server
│   │   ├── analysis_engine.py  # Workout analysis logic
│   │   └── comparison_engine.py # Multi-workout comparison
│   ├── templates/              # HTML templates
│   │   └── index.html         # Main dashboard UI
│   ├── requirements.txt       # Python dependencies
│   └── README.md              # Detailed documentation
└── README.md                   # This file
```

## Legacy Scripts

The root directory contains legacy analysis scripts:
- `analyze_workouts.py` - Standalone workout analysis
- `generate_swim_dashboard.py` - Static dashboard generator
- `plot_hr_vs_pace.py` - Heart rate vs pace analysis
- `convert_fit_to_csv.py` - FIT file converter

These are kept for reference but the main development focus is on the FastAPI dashboard.

## License

See individual files for license information.
