# Swimming Workout Dashboard - FastAPI Application

A full-stack web application for analyzing swimming workouts with automated scoring, visualization, and coaching recommendations.

## Features

- 🔗 **Strava Integration** - Connect your Strava account and analyze swimming workouts automatically
- 📊 **Activity Import** - Load and cache your latest Strava swimming activities
- 🎯 **Automated scoring** (A/B/C/D grades) based on 4 key metrics
- 📈 **Interactive visualizations**:
  - Speed & Stroke Rate trends over time (line charts)
  - Speed vs Efficiency cloud plot
- ✅ **Pros & Cons** analysis
- 📋 **Next workout prescriptions** based on limiters
- 🔄 **Multi-workout comparison** - Compare 2-20 activities to track progress and trends
- 🎨 **Modern, responsive UI** with mobile support
- 🔄 **Background sync** - Automatic activity synchronization (optional)
- ⚡ **Retry logic & rate limiting** - Production-ready error handling

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
   
   **Note**: Database is required for Strava integration features (OAuth token storage, activity caching). The application is designed for Strava integration.
   
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

1. **Connect Strava**: Click "Connect Strava" to authorize the application
2. **Load Activities**: Click "Load Activities" to import your latest swimming workouts
3. **Analyze**: Select one or more activities and click "Analyze Selected" or "Compare Selected"
4. **View Results**: The dashboard will display:
   - Coach summary (headline, constraint, action)
   - Automated scores (Distance, Pace, Stroke, Speed Gears)
   - Grade assignment (A/B/C/D)
   - Pros and cons
   - Next workout prescription
   - Interactive charts and visualizations

## API Endpoints

### `GET /`
Main dashboard page (HTML)

### `POST /strava/analyze-activity/{activity_id}`
Analyze a single Strava activity

**Request**: Query parameter `athlete_id` (optional, uses database token if not provided)

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

### `GET /analytics/pmc`
Get Performance Management Chart (PMC) data for a Strava athlete.

Calculates TSS (Training Stress Score), CTL (Chronic Training Load), ATL (Acute Training Load), and TSB (Training Stress Balance).

**Query Parameters:**
- `athlete_id` (required): Strava athlete ID
- `days` (optional): Number of days to look back (default: 180, max: 365)
- `sport` (optional): Sport filter - 'all', 'swim', 'run', 'ride' (default: 'all')

**Response**: JSON array of daily PMC data points:
```json
[
  {
    "date": "2024-01-15",
    "tss": 45.2,
    "ctl": 38.5,
    "atl": 42.1,
    "tsb": -3.6
  },
  ...
]
```

## Project Structure

```
fastapi_dashboard/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── db.py                   # Database configuration (SQLAlchemy)
│   ├── models.py               # SQLAlchemy ORM models (User, StravaToken, Activity)
│   ├── strava_store.py         # Database operations for Strava (tokens, activities)
│   ├── strava_oauth.py         # Strava OAuth integration
│   ├── strava_converter.py     # Strava data conversion
│   ├── strava_sync.py          # Sync service (incremental sync, retry, rate limiting)
│   ├── strava_retry.py         # Retry logic with exponential backoff
│   ├── strava_rate_limiter.py  # Rate limit tracking and enforcement
│   ├── strava_background_sync.py  # Background sync job
│   ├── analysis_engine.py      # Workout analysis logic
│   └── comparison_engine.py   # Multi-workout comparison
├── migrations/
│   ├── 001_add_users_updated_at.sql  # Database migration scripts
│   └── README.md               # Migration instructions
├── templates/
│   └── index.html              # Frontend HTML with Chart.js
├── static/                     # Static files (if needed)
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── QUICKSTART.md                # Quick setup guide
├── ARCHITECTURE.md              # System architecture documentation
├── SYNC_FEATURES.md             # Sync layer features documentation
└── TROUBLESHOOTING.md           # Troubleshooting guide
```

## Development

The application uses:
- **FastAPI** for the backend API
- **Pandas** for data processing
- **Chart.js** for visualizations
- **Jinja2** for templating

## Strava Integration

The application integrates with Strava API to:
- Authenticate users via OAuth 2.0
- Fetch and cache swimming activities
- Analyze activity streams (speed, cadence, heart rate)
- Provide automated coaching insights

### Environment Variables

Set these in your `.env` file or Render environment:

```bash
STRAVA_ENABLED=true
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REDIRECT_URI=http://localhost:8000/strava/callback  # Local
# or
STRAVA_REDIRECT_URI=https://your-app.onrender.com/strava/callback  # Production
STRAVA_SCOPE=read,activity:read_all

# Optional: Enable background sync
BACKGROUND_SYNC_ENABLED=true
```

See `RENDER_STRAVA_SETUP.md` for detailed setup instructions.

## Notes

- Activities are cached in the database to reduce Strava API calls
- Tokens are automatically refreshed when expired
- Rate limiting and retry logic are built-in for production reliability
- All analysis happens server-side for security
