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
STRAVA_ENABLED = os.getenv("STRAVA_ENABLED", "false").lower() == "true"


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main dashboard page."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "strava_enabled": STRAVA_ENABLED
    })


@app.get("/api/config")
async def get_config():
    """Get application configuration including feature flags."""
    return {
        "strava_enabled": STRAVA_ENABLED
    }


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


if __name__ == "__main__":
    import uvicorn
    import os
    # Use PORT environment variable for Render.com, default to 8000 for local
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
