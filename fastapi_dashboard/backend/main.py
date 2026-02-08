"""
FastAPI backend for swimming workout dashboard.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import os
import sys
import uuid
from pathlib import Path
from typing import Optional, List

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from analysis_engine import analyze_workout
from comparison_engine import analyze_multiple_workouts

# Import database dependencies
try:
    from db import get_db, engine, Base, test_db_connection
    DB_AVAILABLE = engine is not None
    
    # Import models to register them with Base.metadata (if models exist)
    # This is optional - if models don't exist, Base.metadata will be empty
    try:
        from models import User, StravaToken, Activity  # noqa: F401
        print("INFO: Database models imported")
    except ImportError:
        print("INFO: Database models not found - Base.metadata will be empty")
    
    # Auto-create database tables if DB_AUTO_CREATE is set to true
    if DB_AVAILABLE:
        db_auto_create = os.getenv("DB_AUTO_CREATE", "false").lower() in ("true", "1", "yes", "on")
        if db_auto_create:
            try:
                Base.metadata.create_all(bind=engine)
                print("INFO: Database tables auto-created")
                
                # Run migration to add new columns if they don't exist
                try:
                    from migrate_add_athlete_info import migrate_add_athlete_info
                    migrate_add_athlete_info()
                except ImportError:
                    print("INFO: Migration script not found, skipping column migration")
                except Exception as e:
                    print(f"WARNING: Migration failed (this is OK if columns already exist): {e}")
            except Exception as e:
                print(f"WARNING: Failed to auto-create database tables: {e}")
                print("Database features may not work correctly.")
        else:
            print("INFO: DB_AUTO_CREATE not set to true. Skipping automatic table creation.")
            print("      Set DB_AUTO_CREATE=true to automatically create tables on startup.")
    else:
        print("WARNING: DATABASE_URL not set. Database features will be disabled.")
except ImportError:
    DB_AVAILABLE = False
    print("WARNING: Database module not available. Database features disabled.")

app = FastAPI(title="Swimming Workout Dashboard", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories
# Get the fastapi_dashboard directory (parent of backend)
BACKEND_DIR = Path(__file__).parent
BASE_DIR = BACKEND_DIR.parent
UPLOAD_DIR = BASE_DIR / "uploads"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Feature flags from environment variables
# Handle various formats: "true", "True", "TRUE", "1", etc.
_strava_enabled_raw = os.getenv("STRAVA_ENABLED", "false").strip().lower()
STRAVA_ENABLED = _strava_enabled_raw in ("true", "1", "yes", "on")
print(f"DEBUG: STRAVA_ENABLED env var = '{os.getenv('STRAVA_ENABLED', 'NOT SET')}'")
print(f"DEBUG: STRAVA_ENABLED parsed = {STRAVA_ENABLED}")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main dashboard page."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "strava_enabled": STRAVA_ENABLED
    })


@app.get("/api/config")
async def get_config():
    """
    Get application configuration including feature flags and database status.
    
    Returns:
        {
            "strava_enabled": bool,
            "db_connected": bool,
            "strava_token_stored": bool,
            "debug": {...}
        }
    """
    # Debug: Check raw env var value
    raw_value = os.getenv("STRAVA_ENABLED", "NOT_SET")
    
    config = {
        "strava_enabled": STRAVA_ENABLED,
        "db_connected": False,
        "strava_token_stored": False,
        "debug": {
            "STRAVA_ENABLED_raw": raw_value,
            "STRAVA_ENABLED_parsed": STRAVA_ENABLED
        }
    }
    
    # Check database connection
    if DB_AVAILABLE:
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            config["db_connected"] = True
        except Exception:
            config["db_connected"] = False
    
    # Check if Strava token exists (for MVP, we'll check if any token exists)
    # In a multi-user system, this would check for the current user's token
    if config["db_connected"] and STRAVA_ENABLED:
        try:
            from db import get_db
            from models import StravaToken
            
            # Get a database session
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                # Check if any Strava token exists
                token_count = db.query(StravaToken).count()
                config["strava_token_stored"] = token_count > 0
            finally:
                db.close()
        except Exception:
            # If we can't check, assume false
            config["strava_token_stored"] = False
    
    return config


@app.get("/debug/strava-athlete")
async def debug_strava_athlete(athlete_id: Optional[int] = None):
    """
    Debug endpoint to check which Strava athlete we're connected as.
    Calls Strava GET /api/v3/athlete and returns athlete info.
    
    Args:
        athlete_id: Strava athlete ID (query parameter, optional)
        
    Returns:
        {
            "id": int,
            "username": str,
            "firstname": str,
            "lastname": str
        }
    """
    # Import here to avoid circular dependencies
    if not STRAVA_ENABLED:
        return JSONResponse(
            status_code=503,
            content={"error": "Strava integration not enabled"}
        )
    
    try:
        import httpx
        from db import get_db
        from models import User, StravaToken
        from strava_store import ensure_valid_access_token
        
        if not DB_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={"error": "Database not available. Athlete check requires database."}
            )
        
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # If athlete_id not provided, get the most recent token
            if not athlete_id:
                token = db.query(StravaToken).join(User).order_by(StravaToken.updated_at.desc()).first()
                if token and token.user:
                    athlete_id = token.user.strava_athlete_id
                else:
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Not connected to Strava"}
                    )
            
            # Ensure we have a valid access token
            access_token = await ensure_valid_access_token(db, athlete_id)
            
            if not access_token:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Not connected to Strava. No valid token found or refresh failed."}
                )
            
            # Call Strava API to get athlete info
            async with httpx.AsyncClient() as client:
                athlete_response = await client.get(
                    "https://www.strava.com/api/v3/athlete",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0
                )
                
                if athlete_response.status_code == 401 or athlete_response.status_code == 403:
                    error_detail = athlete_response.text
                    try:
                        error_json = athlete_response.json()
                        error_detail = str(error_json)
                    except:
                        pass
                    return JSONResponse(
                        status_code=athlete_response.status_code,
                        content={
                            "error": "strava_error",
                            "details": error_detail
                        }
                    )
                
                athlete_response.raise_for_status()
                athlete_data = athlete_response.json()
                
                return {
                    "id": athlete_data.get("id"),
                    "username": athlete_data.get("username"),
                    "firstname": athlete_data.get("firstname"),
                    "lastname": athlete_data.get("lastname")
                }
        finally:
            db.close()
    except ImportError as e:
        return JSONResponse(
            status_code=503,
            content={"error": "Strava integration not available", "details": str(e)}
        )
    except Exception as e:
        import traceback
        print(f"ERROR: Exception in /debug/strava-athlete: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error checking Strava athlete: {str(e)}"}
        )


# Import Strava OAuth routes if enabled
if STRAVA_ENABLED:
    try:
        # Try relative import first (when running as module)
        try:
            from .strava_oauth import router as strava_router
        except ImportError:
            # Fall back to absolute import (when running directly)
            from strava_oauth import router as strava_router
        
        app.include_router(strava_router)
        print(f"INFO: Strava OAuth routes loaded successfully. Routes available at /strava/*")
    except ImportError as e:
        print(f"WARNING: Could not import Strava OAuth routes: {e}")
        print("Strava features will be disabled.")
        STRAVA_ENABLED = False
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while loading Strava OAuth routes: {e}")
        import traceback
        traceback.print_exc()
        print("Strava features will be disabled.")
        STRAVA_ENABLED = False
else:
    print("INFO: Strava integration is disabled via STRAVA_ENABLED environment variable.")

# Import dev routes only when ENV=dev
ENV = os.getenv("ENV", "").lower()
if ENV == "dev":
    try:
        try:
            from .dev_routes import router as dev_router
        except ImportError:
            from dev_routes import router as dev_router
        
        app.include_router(dev_router)
        print("INFO: Dev routes loaded. Available at /dev/*")
    except ImportError as e:
        print(f"WARNING: Could not import dev routes: {e}")
    except Exception as e:
        print(f"WARNING: Error loading dev routes: {e}")
else:
    print(f"INFO: Dev routes disabled (ENV={ENV}, not 'dev')")


@app.post("/api/analyze")
async def analyze_workout_file(file: UploadFile = File(...)):
    """
    Analyze uploaded CSV workout file.
    
    Returns:
        JSON with analysis results including:
        - metadata (date, distance, time, etc.)
        - metrics (scores, CV, etc.)
        - grade (A/B/C/D)
        - sub_scores
        - pros/cons
        - prescription
    """
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    # Save uploaded file
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}.csv"
    
    try:
        # Read and save file
        contents = await file.read()
        with open(file_path, 'wb') as f:
            f.write(contents)
        
        # Load CSV
        df = pd.read_csv(file_path)
        
        if df.empty:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        # Analyze workout
        analysis = analyze_workout(df)
        
        # Clean up uploaded file
        if file_path.exists():
            os.remove(file_path)
        
        # Convert to JSON-serializable format (handle any remaining NumPy types)
        def make_serializable(obj):
            if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            elif pd.isna(obj):
                return None
            return obj
        
        # Ensure all values are JSON serializable
        serializable_analysis = make_serializable(analysis)
        
        return JSONResponse(content=serializable_analysis)
    
    except pd.errors.EmptyDataError:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=400, detail="CSV file is empty or invalid")
    except Exception as e:
        # Clean up on error
        if file_path.exists():
            os.remove(file_path)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error analyzing file: {str(e)}")


@app.post("/api/compare")
async def compare_workouts(files: List[UploadFile] = File(...)):
    """
    Compare multiple uploaded CSV workout files.
    
    Returns:
        JSON with comparison analysis including:
        - Individual workout analyses
        - Time series data
        - Trends
        - Coach insights
        - Strengths and weaknesses
        - Training recommendations
    """
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Please upload at least 2 CSV files for comparison")
    
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files allowed for comparison")
    
    workout_dataframes = []
    file_paths = []
    
    try:
        # Process all uploaded files
        for file in files:
            if not file.filename.endswith('.csv'):
                continue
            
            # Save uploaded file
            file_id = str(uuid.uuid4())
            file_path = UPLOAD_DIR / f"{file_id}.csv"
            file_paths.append(file_path)
            
            # Read and save file
            contents = await file.read()
            with open(file_path, 'wb') as f:
                f.write(contents)
            
            # Load CSV
            df = pd.read_csv(file_path)
            if not df.empty:
                workout_dataframes.append(df)
        
        if len(workout_dataframes) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 valid CSV files for comparison")
        
        # Analyze multiple workouts
        comparison = analyze_multiple_workouts(workout_dataframes)
        
        # Clean up uploaded files
        for file_path in file_paths:
            if file_path.exists():
                os.remove(file_path)
        
        # Convert to JSON-serializable format
        def make_serializable(obj):
            if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            elif pd.isna(obj):
                return None
            return obj
        
        serializable_comparison = make_serializable(comparison)
        
        return JSONResponse(content=serializable_comparison)
    
    except Exception as e:
        # Clean up on error
        for file_path in file_paths:
            if file_path.exists():
                os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error comparing workouts: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "Swimming Dashboard API is running"}


@app.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify API is working."""
    return {
        "status": "ok",
        "message": "API is working",
        "test_data": {
            "grade": "B",
            "total_score": 75,
            "workout_type": "Endurance"
        }
    }


@app.get("/api/db-test")
async def db_test():
    """
    Test database connection.
    
    Returns:
        {"db_connected": true} if connection successful
        {"db_connected": false, "error": "..."} if connection fails
    """
    if not DB_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={
                "db_connected": False,
                "error": "Database not configured. Set DATABASE_URL environment variable."
            }
        )
    
    # Use test_db_connection function
    success, error_msg = test_db_connection()
    
    if success:
        return {"db_connected": True}
    else:
        return JSONResponse(
            status_code=500,
            content={
                "db_connected": False,
                "error": error_msg
            }
        )


@app.get("/api/db-status")
async def db_status():
    """
    Check database status - whether tables exist and basic query works.
    
    Returns:
        {
            "tables_exist": bool,
            "user_count": int (if tables exist),
            "existing_tables": list (if available),
            "error": str (if error occurred)
        }
    """
    if not DB_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={
                "tables_exist": False,
                "error": "Database not configured. Set DATABASE_URL environment variable."
            }
        )
    
    try:
        from sqlalchemy import inspect, text
        from sqlalchemy.orm import Session
        
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        # Check if our tables exist
        required_tables = {"users", "strava_tokens", "activities"}
        tables_exist = required_tables.issubset(set(table_names))
        
        if not tables_exist:
            status = {
                "tables_exist": False,
                "existing_tables": table_names,
                "required_tables": list(required_tables),
                "error": f"Missing tables. Found: {table_names}, Required: {list(required_tables)}"
            }
            status_code = 503
        else:
            # If tables exist, try to count users
            with Session(engine) as session:
                result = session.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
            
            status = {
                "tables_exist": True,
                "user_count": user_count,
                "existing_tables": table_names
            }
            status_code = 200
        
        return JSONResponse(status_code=status_code, content=status)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "tables_exist": False,
                "error": f"Error checking database status: {str(e)}"
            }
        )


@app.get("/api/activities")
async def get_activities(athlete_id: Optional[int] = None, limit: int = 10):
    """
    Get cached activities from database for a given athlete.
    
    Args:
        athlete_id: Strava athlete ID (query parameter, required)
        limit: Maximum number of activities to return (default: 10, max: 100)
        
    Returns:
        {
            "count": int,
            "activities": [
                {
                    "id": int,
                    "name": str (from raw_json),
                    "type": str,
                    "start_date": str,
                    "distance": float
                }
            ]
        }
    """
    if not athlete_id:
        raise HTTPException(
            status_code=400,
            detail="athlete_id query parameter is required"
        )
    
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 100"
        )
    
    if not DB_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Activity caching requires database."
        )
    
    try:
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Find user by athlete_id
            user = db.query(User).filter(User.strava_athlete_id == athlete_id).first()
            
            if not user:
                return {
                    "count": 0,
                    "activities": []
                }
            
            # Query activities sorted by start_date desc
            activities = db.query(Activity).filter(
                Activity.user_id == user.id
            ).order_by(
                Activity.start_date.desc()
            ).limit(limit).all()
            
            # Format activities for response
            formatted_activities = []
            for activity in activities:
                # Get name from raw_json if available
                name = "Untitled"
                if activity.raw_json and isinstance(activity.raw_json, dict):
                    name = activity.raw_json.get("name", "Untitled")
                
                # Format start_date
                start_date_str = None
                if activity.start_date:
                    start_date_str = activity.start_date.isoformat()
                elif activity.raw_json and isinstance(activity.raw_json, dict):
                    start_date_str = activity.raw_json.get("start_date")
                
                formatted_activities.append({
                    "id": activity.id,
                    "name": name,
                    "type": activity.type or "Unknown",
                    "start_date": start_date_str,
                    "distance": activity.distance_m or 0
                })
            
            return {
                "count": len(formatted_activities),
                "activities": formatted_activities
            }
        
        finally:
            db.close()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to get activities: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving activities: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    import os
    # Use PORT environment variable for Render.com, default to 8000 for local
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
