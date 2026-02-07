"""
Strava OAuth integration for importing workouts.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
import os
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None
    print("Warning: httpx not installed. Strava features will not work.")

router = APIRouter(prefix="/strava", tags=["strava"])

# Strava OAuth configuration
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID", "")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "")
STRAVA_REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI", "")

# In-memory token storage (in production, use database or secure storage)
# Key: user_id (for now, using session or simple identifier)
strava_tokens = {}


@router.get("/login")
async def strava_login():
    """
    Redirect user to Strava OAuth authorization page.
    """
    if httpx is None:
        raise HTTPException(
            status_code=500,
            detail="httpx library not installed. Please install dependencies: pip install httpx"
        )
    
    if not STRAVA_CLIENT_ID or not STRAVA_REDIRECT_URI:
        raise HTTPException(
            status_code=500,
            detail="Strava OAuth not configured. Please set STRAVA_CLIENT_ID and STRAVA_REDIRECT_URI."
        )
    
    # Strava OAuth authorization URL
    auth_url = (
        f"https://www.strava.com/oauth/authorize?"
        f"client_id={STRAVA_CLIENT_ID}&"
        f"redirect_uri={STRAVA_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=activity:read_all"
    )
    
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def strava_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    """
    Handle Strava OAuth callback and exchange code for access token.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"Strava authorization error: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received from Strava")
    
    if not STRAVA_CLIENT_ID or not STRAVA_CLIENT_SECRET or not STRAVA_REDIRECT_URI:
        raise HTTPException(
            status_code=500,
            detail="Strava OAuth not configured. Please set STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, and STRAVA_REDIRECT_URI."
        )
    
    if httpx is None:
        raise HTTPException(
            status_code=500,
            detail="httpx library not installed. Please install dependencies: pip install httpx"
        )
    
    # Exchange authorization code for access token
    # IMPORTANT: The redirect_uri must match EXACTLY what was used in the authorization request
    # Also, authorization codes can only be used once and expire quickly
    try:
        # Log the redirect URI being used for debugging
        print(f"DEBUG: Using redirect_uri: {STRAVA_REDIRECT_URI}")
        print(f"DEBUG: Client ID: {STRAVA_CLIENT_ID}")
        print(f"DEBUG: Code received: {code[:20]}...")
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://www.strava.com/oauth/token",
                data={
                    "client_id": STRAVA_CLIENT_ID,
                    "client_secret": STRAVA_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": STRAVA_REDIRECT_URI  # Must match authorization request exactly
                },
                timeout=10.0
            )
            
            # Check for errors in response
            if token_response.status_code != 200:
                error_detail = token_response.text
                try:
                    error_json = token_response.json()
                    error_detail = str(error_json)
                except:
                    pass
                raise HTTPException(
                    status_code=token_response.status_code,
                    detail=f"Strava token exchange failed: {error_detail}"
                )
            
            token_data = token_response.json()
            
            # Store tokens (in production, use database with user session)
            # For now, using a simple identifier - in production, use actual user session
            user_id = "default_user"  # TODO: Get from session
            strava_tokens[user_id] = {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_at": token_data.get("expires_at"),
                "athlete": token_data.get("athlete", {})
            }
            
            # Redirect back to dashboard with success message
            return RedirectResponse(url="/?strava_connected=true")
    
    except HTTPException:
        # Re-raise HTTPException as-is (don't wrap it)
        raise
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        try:
            error_json = e.response.json()
            error_detail = str(error_json)
        except:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"Failed to exchange code for token: {error_detail}"
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error during Strava OAuth: {str(e)}\n\nTraceback:\n{error_trace}"
        )


@router.get("/import-latest")
async def import_latest_activity():
    """
    Fetch latest activities from Strava API.
    Returns list of recent activities.
    """
    user_id = "default_user"  # TODO: Get from session
    
    if user_id not in strava_tokens:
        raise HTTPException(
            status_code=401,
            detail="Not connected to Strava. Please connect your Strava account first."
        )
    
    tokens = strava_tokens[user_id]
    access_token = tokens.get("access_token")
    
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="No access token found. Please reconnect your Strava account."
        )
    
    if httpx is None:
        raise HTTPException(
            status_code=500,
            detail="httpx library not installed. Please install dependencies: pip install httpx"
        )
    
    # Fetch athlete activities from Strava API
    try:
        async with httpx.AsyncClient() as client:
            activities_response = await client.get(
                "https://www.strava.com/api/v3/athlete/activities",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"per_page": 30}  # Get last 30 activities
            )
            activities_response.raise_for_status()
            activities = activities_response.json()
            
            # Filter for swimming activities and format for frontend
            formatted_activities = []
            for activity in activities:
                formatted_activities.append({
                    "id": activity.get("id"),
                    "name": activity.get("name", "Untitled"),
                    "type": activity.get("sport_type", "Unknown"),
                    "distance": activity.get("distance", 0),  # meters
                    "duration": activity.get("elapsed_time", 0),  # seconds
                    "start_date": activity.get("start_date"),
                    "is_swim": activity.get("sport_type", "").lower() == "swim"
                })
            
            return {
                "status": "success",
                "count": len(formatted_activities),
                "activities": formatted_activities
            }
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Strava access token expired or invalid. Please reconnect your Strava account."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch activities from Strava: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching Strava activities: {str(e)}"
        )


@router.get("/status")
async def strava_status():
    """
    Check if user is connected to Strava.
    """
    user_id = "default_user"  # TODO: Get from session
    
    is_connected = user_id in strava_tokens and strava_tokens[user_id].get("access_token")
    
    return {
        "connected": is_connected,
        "athlete": strava_tokens[user_id].get("athlete", {}) if is_connected else None
    }


@router.post("/analyze-activity/{activity_id}")
async def analyze_strava_activity(activity_id: int):
    """
    Fetch Strava activity streams and analyze using workout analysis engine.
    """
    user_id = "default_user"  # TODO: Get from session
    
    if user_id not in strava_tokens:
        raise HTTPException(
            status_code=401,
            detail="Not connected to Strava. Please connect your Strava account first."
        )
    
    tokens = strava_tokens[user_id]
    access_token = tokens.get("access_token")
    
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="No access token found. Please reconnect your Strava account."
        )
    
    if httpx is None:
        raise HTTPException(
            status_code=500,
            detail="httpx library not installed. Please install dependencies: pip install httpx"
        )
    
    try:
        import sys
        from pathlib import Path
        # Add backend directory to path for imports
        backend_dir = Path(__file__).parent
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        
        from strava_converter import strava_streams_to_dataframe, is_swimming_activity
        from analysis_engine import analyze_workout
        
        async with httpx.AsyncClient() as client:
            # Fetch activity details
            activity_response = await client.get(
                f"https://www.strava.com/api/v3/activities/{activity_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            activity_response.raise_for_status()
            activity = activity_response.json()
            
            # Check if it's a swimming activity
            if not is_swimming_activity(activity):
                raise HTTPException(
                    status_code=400,
                    detail=f"This activity is {activity.get('sport_type', 'unknown')}, not a swimming workout."
                )
            
            # Fetch activity streams (detailed time-series data)
            streams_response = await client.get(
                f"https://www.strava.com/api/v3/activities/{activity_id}/streams",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "keys": "time,distance,velocity_smooth,cadence,heartrate",
                    "key_by_type": "true"
                }
            )
            
            streams = {}
            if streams_response.status_code == 200:
                streams_data = streams_response.json()
                
                # With key_by_type=true, Strava returns a dict keyed by stream type
                # Each value is a dict with 'data' and 'series_type' keys
                if isinstance(streams_data, dict):
                    # Already in the format we need - use as-is
                    streams = streams_data
                elif isinstance(streams_data, list):
                    # Convert list format to dict format
                    for stream in streams_data:
                        if isinstance(stream, dict) and 'type' in stream:
                            streams[stream['type']] = {
                                'data': stream.get('data', []),
                                'series_type': stream.get('series_type', 'time')
                            }
                else:
                    # Unexpected format - log and use empty dict
                    print(f"Warning: Unexpected streams format: {type(streams_data)}")
                    streams = {}
            
            # Convert Strava data to DataFrame
            df = strava_streams_to_dataframe(activity, streams)
            
            if df.empty or len(df) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No data available for this activity. Stream data may not be available."
                )
            
            # Analyze using existing analysis engine
            analysis_result = analyze_workout(df)
            
            return analysis_result
    
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Activity not found")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Strava activity: {e.response.text}"
        )
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing Strava activity: {str(e)}\n\n{traceback.format_exc()}"
        )
