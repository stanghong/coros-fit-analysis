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

4. (Optional) Set up database connection:
   
   Create a `.env` file in the `fastapi_dashboard` directory:
   ```bash
   # For local PostgreSQL
   DATABASE_URL=postgresql://user:password@localhost:5432/coros_fit?sslmode=require
   
   # For Supabase
   DATABASE_URL=postgresql://postgres:[PASSWORD]@[PROJECT].supabase.co:5432/postgres?sslmode=require
   ```
   
   **Important**: If your password contains special characters (@, #, %, etc.), 
   you must URL-encode them (e.g., `@` becomes `%40`).
   
   **Auto-create tables**: To automatically create database tables on startup, add:
   ```bash
   DB_AUTO_CREATE=true
   ```
   ⚠️  **Warning**: Only set this in development. In production, use proper migrations.
   
   **Note**: Database is required for Strava integration features (OAuth token storage, activity caching). CSV upload and analysis work without a database.
   
   Test the connection:
   ```bash
   curl http://localhost:8000/api/db-test
   ```

5. **Database Migrations** (if needed):
   
   If you see errors like `column users.updated_at does not exist`, run the migration:
   
   - **Quick fix**: See `MIGRATION_GUIDE.md` for step-by-step instructions
   - **Migration files**: Located in `migrations/` directory
   - **Run once**: Copy SQL from `migrations/001_add_users_updated_at.sql` and run in Supabase SQL Editor
   
   See `migrations/README.md` for detailed migration instructions.

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

### `GET /api/db-test`
Test database connection

**Response**: 
```json
{"db_connected": true}
```
or
```json
{"db_connected": false, "error": "..."}
```

### `GET /api/db-status`
Check database status - whether tables exist and basic query works

**Response**:
```json
{
  "tables_exist": true,
  "user_count": 0,
  "existing_tables": ["users", "strava_tokens", "activities"]
}
```
or if tables don't exist:
```json
{
  "tables_exist": false,
  "error": "Missing tables...",
  "existing_tables": [],
  "required_tables": ["users", "strava_tokens", "activities"]
}
```

## Project Structure

```
fastapi_dashboard/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── db.py                   # Database configuration (SQLAlchemy)
│   ├── models.py               # SQLAlchemy ORM models (User, StravaToken, Activity)
│   ├── strava_store.py         # Database operations for Strava (tokens, activities)
│   ├── analysis_engine.py      # Workout analysis logic
│   ├── comparison_engine.py   # Multi-workout comparison
│   ├── strava_oauth.py         # Strava OAuth integration
│   └── strava_converter.py     # Strava data conversion
├── migrations/
│   ├── 001_add_users_updated_at.sql  # Database migration scripts
│   └── README.md               # Migration instructions
├── templates/
│   └── index.html              # Frontend HTML with Chart.js
├── static/                     # Static files (if needed)
├── uploads/                     # Temporary file storage
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── QUICKSTART.md                # Quick setup guide
├── COMPARISON_FEATURE.md        # Comparison feature docs
├── ARCHITECTURE.md              # System architecture documentation
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
