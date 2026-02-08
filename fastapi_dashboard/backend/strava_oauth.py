"""
Strava OAuth integration for importing workouts.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
import os
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None
    print("Warning: httpx not installed. Strava features will not work.")

# Import database dependencies
try:
    from db import get_db
    from models import User, StravaToken
    from strava_store import get_or_create_user, upsert_strava_token, ensure_valid_access_token, get_token_for_athlete, upsert_activity
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("Warning: Database not available. Token persistence will not work.")

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
async def strava_callback(
    request: Request,
    code: Optional[str] = None,
    error: Optional[str] = None
):
    """
    Handle Strava OAuth callback and exchange code for access token.
    Persists tokens to database if available.
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
        # Log the redirect URI being used for debugging (but not secrets)
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
            
            # Extract athlete ID and token information
            athlete = token_data.get("athlete", {})
            athlete_id = athlete.get("id")
            
            if not athlete_id:
                raise HTTPException(
                    status_code=500,
                    detail="No athlete ID in Strava response"
                )
            
            # Get fresh athlete info from Strava API using the new access token
            access_token = token_data.get("access_token")
            athlete_info = None
            if access_token and httpx:
                try:
                    async with httpx.AsyncClient() as client:
                        athlete_response = await client.get(
                            "https://www.strava.com/api/v3/athlete",
                            headers={"Authorization": f"Bearer {access_token}"},
                            timeout=10.0
                        )
                        if athlete_response.status_code == 200:
                            athlete_info = athlete_response.json()
                            print(f"INFO: Fetched athlete info: id={athlete_info.get('id')}, "
                                  f"username={athlete_info.get('username')}, "
                                  f"firstname={athlete_info.get('firstname')}, "
                                  f"lastname={athlete_info.get('lastname')}")
                        else:
                            print(f"WARNING: Failed to fetch athlete info: {athlete_response.status_code} - {athlete_response.text}")
                except Exception as e:
                    print(f"WARNING: Exception fetching athlete info: {str(e)}")
            
            # Persist tokens to database if available
            if DB_AVAILABLE:
                try:
                    # Get database session
                    db_gen = get_db()
                    db = next(db_gen)
                    
                    try:
                        # Prepare athlete info dict for user creation/update
                        athlete_info_dict = None
                        if athlete_info:
                            athlete_info_dict = {
                                "username": athlete_info.get("username"),
                                "firstname": athlete_info.get("firstname"),
                                "lastname": athlete_info.get("lastname")
                            }
                        
                        # Get or create user for this athlete (with athlete info)
                        user = get_or_create_user(db, athlete_id, athlete_info_dict)
                        
                        # Prepare token payload
                        token_payload = {
                            "access_token": token_data.get("access_token"),
                            "refresh_token": token_data.get("refresh_token"),
                            "expires_at": token_data.get("expires_at"),
                            "scope": token_data.get("scope")
                        }
                        
                        # Upsert token
                        upsert_strava_token(db, user.id, token_payload)
                        
                        print(f"INFO: Strava tokens persisted for athlete_id={athlete_id}, user_id={user.id}, "
                              f"username={user.strava_username}, name={user.strava_firstname} {user.strava_lastname}")
                    finally:
                        db.close()
                except Exception as e:
                    # Log error but don't fail the OAuth flow
                    print(f"WARNING: Failed to persist tokens to database: {str(e)}")
                    # Fall back to in-memory storage
                    user_id = "default_user"
                    strava_tokens[user_id] = {
                        "access_token": token_data.get("access_token"),
                        "refresh_token": token_data.get("refresh_token"),
                        "expires_at": token_data.get("expires_at"),
                        "athlete": athlete
                    }
            else:
                # Fall back to in-memory storage if database not available
                print("WARNING: Database not available, storing tokens in-memory only")
                user_id = "default_user"
                strava_tokens[user_id] = {
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_at": token_data.get("expires_at"),
                    "athlete": athlete
                }
            
            # Return simple HTML success page with auto-redirect
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Strava Connected</title>
                <meta http-equiv="refresh" content="3;url=/?strava_connected=true">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }}
                    .container {{
                        text-align: center;
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    }}
                    h1 {{
                        color: #667eea;
                        margin-bottom: 20px;
                    }}
                    p {{
                        color: #666;
                        margin-bottom: 30px;
                    }}
                    a {{
                        display: inline-block;
                        padding: 12px 24px;
                        background: #667eea;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        transition: background 0.3s;
                    }}
                    a:hover {{
                        background: #5568d3;
                    }}
                    .countdown {{
                        color: #999;
                        font-size: 0.9em;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>✅ Strava Connected</h1>
                    <p>Your Strava account has been successfully connected!</p>
                    <a href="/?strava_connected=true">Go to Dashboard</a>
                    <p class="countdown">Redirecting automatically in 3 seconds...</p>
                </div>
                <script>
                    // Suppress browser extension errors (they're harmless)
                    window.addEventListener('error', function(e) {{
                        if (e.message && e.message.includes('message channel closed')) {{
                            e.preventDefault();
                            return false;
                        }}
                    }}, true);
                    
                    // Auto-redirect after 3 seconds
                    setTimeout(function() {{
                        window.location.href = '/?strava_connected=true';
                    }}, 3000);
                </script>
            </body>
            </html>
            """)
    
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
async def import_latest_activity(athlete_id: Optional[int] = None, limit: int = 10):
    """
    Fetch latest activities from Strava API and cache them in the database.
    
    Args:
        athlete_id: Strava athlete ID (query parameter, required)
        limit: Maximum number of activities to import (default: 10, max: 200)
        
    Returns:
        {
            "status": "success",
            "count": int,
            "activities": [
                {
                    "id": int,
                    "name": str,
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
    
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 200"
        )
    
    if not DB_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Activity caching requires database."
        )
    
    if httpx is None:
        raise HTTPException(
            status_code=500,
            detail="httpx library not installed. Please install dependencies: pip install httpx"
        )
    
    try:
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Ensure we have a valid access token (refresh if needed)
            access_token = await ensure_valid_access_token(db, athlete_id)
            
            if not access_token:
                # Check if token exists but refresh failed
                token = get_token_for_athlete(db, athlete_id)
                if token:
                    # Log token details for debugging
                    current_time = int(time.time())
                    print(f"DEBUG: Token exists but refresh failed or token invalid")
                    print(f"DEBUG: Token expires_at: {token.expires_at}, current_time: {current_time}")
                    print(f"DEBUG: Token expired: {token.expires_at <= current_time}")
                    print(f"DEBUG: Has refresh_token: {bool(token.refresh_token)}")
                    raise HTTPException(
                        status_code=401,
                        detail="Strava access token expired or invalid. The token refresh may have failed. Please reconnect your Strava account."
                    )
                else:
                    raise HTTPException(
                        status_code=401,
                        detail="No valid token found for this athlete_id. Please reconnect Strava."
                    )
            
            # Get or create user for this athlete
            user = get_or_create_user(db, athlete_id)
            
            # Fetch activities from Strava API
            async with httpx.AsyncClient() as client:
                activities_response = await client.get(
                    "https://www.strava.com/api/v3/athlete/activities",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"per_page": limit, "page": 1}
                )
                activities_response.raise_for_status()
                activities = activities_response.json()
            
            # Always log first 5 activities for debugging (do NOT log tokens/secrets)
            if activities:
                print(f"INFO: First {min(5, len(activities))} activities from Strava (page 1):")
                for i, activity in enumerate(activities[:5], 1):
                    print(f"  {i}. name={activity.get('name')}, "
                          f"start_date={activity.get('start_date')}, "
                          f"type={activity.get('type')}, "
                          f"sport_type={activity.get('sport_type')}, "
                          f"private={activity.get('private')}")
            
            # Upsert each activity into database
            imported_activities = []
            for activity_data in activities:
                try:
                    # Prepare activity data with raw_json
                    activity_payload = {
                        "id": activity_data.get("id"),
                        "sport_type": activity_data.get("sport_type"),
                        "type": activity_data.get("type"),
                        "start_date": activity_data.get("start_date"),
                        "distance": activity_data.get("distance"),
                        "moving_time": activity_data.get("moving_time"),
                        "elapsed_time": activity_data.get("elapsed_time"),
                        "average_heartrate": activity_data.get("average_heartrate"),
                        "max_heartrate": activity_data.get("max_heartrate"),
                        "total_elevation_gain": activity_data.get("total_elevation_gain"),
                        "raw_json": activity_data  # Store full response
                    }
                    
                    # Upsert activity
                    activity = upsert_activity(db, user.id, activity_payload)
                    
                    # Format for response
                    imported_activities.append({
                        "id": activity.id,
                        "name": activity_data.get("name", "Untitled"),
                        "type": activity.type or activity_data.get("sport_type", "Unknown"),
                        "start_date": activity_data.get("start_date"),
                        "distance": activity.distance_m or 0
                    })
                except Exception as e:
                    print(f"WARNING: Failed to upsert activity {activity_data.get('id')}: {str(e)}")
                    # Continue with other activities
                    continue
            
            # Filter for swimming activities with robust matching
            swim_activities = []
            for activity in imported_activities:
                # Get the full activity data from raw_json if available
                activity_data = None
                for a in activities:
                    if a.get("id") == activity["id"]:
                        activity_data = a
                        break
                
                if activity_data:
                    sport_type = (activity_data.get("sport_type") or "").lower()
                    activity_type = (activity_data.get("type") or "").lower()
                    
                    # Check if it's a swim: sport_type or type contains "swim"
                    is_swim = (
                        "swim" in sport_type or 
                        "swim" in activity_type or
                        sport_type in ("swim", "openwaterswim") or
                        activity_type == "swim"
                    )
                    
                    if is_swim:
                        activity["is_swim"] = True
                        swim_activities.append(activity)
                    else:
                        activity["is_swim"] = False
                else:
                    # Fallback: check type field
                    activity_type = (activity.get("type") or "").lower()
                    if "swim" in activity_type:
                        activity["is_swim"] = True
                        swim_activities.append(activity)
                    else:
                        activity["is_swim"] = False
            
            # Collect distinct sport_type and type values for diagnostics
            distinct_sport_types = set()
            distinct_types = set()
            for activity_data in activities:
                if activity_data.get("sport_type"):
                    distinct_sport_types.add(activity_data.get("sport_type"))
                if activity_data.get("type"):
                    distinct_types.add(activity_data.get("type"))
            
            # Log swim filtering results with diagnostics
            print(f"INFO: Imported {len(imported_activities)} activities, found {len(swim_activities)} swimming activities")
            if len(swim_activities) == 0 and len(imported_activities) > 0:
                print(f"WARNING: No swimming activities found in {len(imported_activities)} activities from page 1. "
                      f"Distinct sport_type values: {sorted(distinct_sport_types)}, "
                      f"Distinct type values: {sorted(distinct_types)}")
            
            return {
                "status": "success",
                "count": len(imported_activities),
                "swim_count": len(swim_activities),
                "pages_fetched": 1,
                "activities": imported_activities,
                "swim_activities": swim_activities,
                "diagnostics": {
                    "distinct_sport_types": sorted(list(distinct_sport_types)),
                    "distinct_types": sorted(list(distinct_types)),
                    "total_scanned": len(imported_activities)
                } if len(swim_activities) == 0 else None
            }
        
        finally:
            db.close()
    
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            # Token expired or invalid - refresh might have failed
            # Check if it's a token issue or something else
            error_text = e.response.text
            if "invalid" in error_text.lower() or "expired" in error_text.lower():
                raise HTTPException(
                    status_code=401,
                    detail="Strava access token expired or invalid. The token refresh may have failed. Please reconnect your Strava account."
                )
            raise HTTPException(
                status_code=401,
                detail="Strava access token expired or invalid. Please reconnect your Strava account."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch activities from Strava: {e.response.text}"
        )
    except Exception as e:
        import traceback
        print(f"ERROR: Failed to import activities: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error importing Strava activities: {str(e)}"
        )


@router.get("/status")
async def strava_status():
    """
    Check if user is connected to Strava.
    Returns connection status and athlete information including athlete_id.
    """
    # Try database first
    if DB_AVAILABLE:
        try:
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                # Get any user with a token (for MVP, get the first one)
                from models import User, StravaToken
                token = db.query(StravaToken).join(User).order_by(StravaToken.updated_at.desc()).first()
                
                if token and token.user:
                    # Get athlete info from raw_json or construct from user
                    athlete_id = token.user.strava_athlete_id
                    print(f"DEBUG: /strava/status returning athlete_id={athlete_id} for user_id={token.user.id}")
                    return {
                        "connected": True,
                        "athlete_id": athlete_id,
                        "athlete": {
                            "id": athlete_id,
                            "username": token.user.strava_username,
                            "firstname": token.user.strava_firstname or "User",
                            "lastname": token.user.strava_lastname or ""
                        }
                    }
                else:
                    print("DEBUG: /strava/status - No token found in database")
            finally:
                db.close()
        except Exception as e:
            print(f"WARNING: Error checking database for Strava status: {e}")
    
    # Fall back to in-memory storage
    user_id = "default_user"  # TODO: Get from session
    
    is_connected = user_id in strava_tokens and strava_tokens[user_id].get("access_token")
    athlete_data = strava_tokens[user_id].get("athlete", {}) if is_connected else None
    
    return {
        "connected": is_connected,
        "athlete_id": athlete_data.get("id") if athlete_data else None,
        "athlete": athlete_data
    }


@router.get("/debug/strava-athlete")
async def debug_strava_athlete(athlete_id: Optional[int] = None):
    """
    Debug endpoint to check which Strava athlete we're connected as.
    Calls Strava GET /api/v3/athlete and returns athlete info.
    
    Args:
        athlete_id: Strava athlete ID (query parameter, optional - will use most recent if not provided)
        
    Returns:
        {
            "id": int,
            "username": str,
            "firstname": str,
            "lastname": str
        }
    """
    if not DB_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={"error": "Database not available. Athlete check requires database."}
        )
    
    if httpx is None:
        return JSONResponse(
            status_code=500,
            content={"error": "httpx library not installed"}
        )
    
    try:
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # If athlete_id not provided, get the most recent token
            if not athlete_id:
                from models import User, StravaToken
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
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"ERROR: Exception in debug_strava_athlete: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error checking Strava athlete: {str(e)}"}
        )


@router.get("/token-check")
async def token_check(athlete_id: Optional[int] = None):
    """
    Check and refresh Strava token if needed.
    
    Args:
        athlete_id: Strava athlete ID (query parameter, required for MVP)
        
    Returns:
        {
            "valid": bool,
            "expires_at": int (Unix timestamp) if valid,
            "error": str if invalid/error,
            "debug": dict with token details (for debugging)
        }
    """
    if not athlete_id:
        raise HTTPException(
            status_code=400,
            detail="athlete_id query parameter is required"
        )
    
    if not DB_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Token check requires database."
        )
    
    try:
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Ensure we have a valid access token (refresh if needed)
            access_token = await ensure_valid_access_token(db, athlete_id)
            
            if not access_token:
                return {
                    "valid": False,
                    "error": "No token found for this athlete_id. Please reconnect Strava."
                }
            
            # Get token to check expires_at
            token = get_token_for_athlete(db, athlete_id)
            
            if not token:
                return {
                    "valid": False,
                    "error": "Token record not found"
                }
            
            # Return success with expires_at (but not the token itself)
            return {
                "valid": True,
                "expires_at": token.expires_at
            }
        
        finally:
            db.close()
    
    except HTTPException:
        raise
    except Exception as e:
        # Safe error handling - don't leak internal details
        print(f"ERROR: Token check failed for athlete_id={athlete_id}: {str(e)}")
        return {
            "valid": False,
            "error": "Failed to check token status"
        }


@router.post("/analyze-activities")
async def analyze_multiple_strava_activities(request: Request, athlete_id: Optional[int] = None):
    """
    Analyze multiple Strava activities and compare them.
    
    Request body: JSON array of activity IDs [123, 456, 789]
    Query parameter: athlete_id (required)
    """
    try:
        activity_ids = await request.json()
        if not isinstance(activity_ids, list):
            raise HTTPException(status_code=400, detail="Request body must be a JSON array of activity IDs")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {str(e)}")
    
    if not DB_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Please configure DATABASE_URL."
        )
    
    if not athlete_id:
        raise HTTPException(
            status_code=400,
            detail="athlete_id query parameter is required"
        )
    
    # Get valid access token from database (auto-refreshes if expired)
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            access_token = await ensure_valid_access_token(db, athlete_id)
            if not access_token:
                raise HTTPException(
                    status_code=401,
                    detail="Not connected to Strava. Please connect your Strava account first."
                )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to get access token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Not connected to Strava. Please connect your Strava account first."
        )
    
    if httpx is None:
        raise HTTPException(
            status_code=500,
            detail="httpx library not installed. Please install dependencies: pip install httpx"
        )
    
    if not activity_ids or len(activity_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="Please select at least 2 activities to compare"
        )
    
    if len(activity_ids) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 activities allowed for comparison"
        )
    
    try:
        import sys
        from pathlib import Path
        backend_dir = Path(__file__).parent
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        
        from strava_converter import strava_streams_to_dataframe, is_swimming_activity
        from comparison_engine import analyze_multiple_workouts
        
        all_dataframes = []
        
        async with httpx.AsyncClient() as client:
            for activity_id in activity_ids:
                # Fetch activity details
                activity_response = await client.get(
                    f"https://www.strava.com/api/v3/activities/{activity_id}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                activity_response.raise_for_status()
                activity = activity_response.json()
                
                # Check if it's a swimming activity
                if not is_swimming_activity(activity):
                    continue  # Skip non-swimming activities
                
                # Fetch activity streams
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
                    if isinstance(streams_data, dict):
                        streams = streams_data
                    elif isinstance(streams_data, list):
                        for stream in streams_data:
                            if isinstance(stream, dict) and 'type' in stream:
                                streams[stream['type']] = {
                                    'data': stream.get('data', []),
                                    'series_type': stream.get('series_type', 'time')
                                }
                
                # Convert to DataFrame
                df = strava_streams_to_dataframe(activity, streams)
                if not df.empty and len(df) > 0:
                    all_dataframes.append(df)
        
        if len(all_dataframes) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough valid swimming activities found. Need at least 2, found {len(all_dataframes)}"
            )
        
        # Analyze using comparison engine
        comparison_result = analyze_multiple_workouts(all_dataframes)
        
        return comparison_result
    
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="One or more activities not found")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Strava activities: {e.response.text}"
        )
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing Strava activities: {str(e)}\n\n{traceback.format_exc()}"
        )


@router.post("/analyze-activity/{activity_id}")
async def analyze_strava_activity(activity_id: int, athlete_id: Optional[int] = None):
    """
    Fetch Strava activity streams and analyze using workout analysis engine.
    """
    if not DB_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Please configure DATABASE_URL."
        )
    
    if not athlete_id:
        raise HTTPException(
            status_code=400,
            detail="athlete_id query parameter is required"
        )
    
    # Get valid access token from database (auto-refreshes if expired)
    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            access_token = await ensure_valid_access_token(db, athlete_id)
            if not access_token:
                raise HTTPException(
                    status_code=401,
                    detail="Not connected to Strava. Please connect your Strava account first."
                )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to get access token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Not connected to Strava. Please connect your Strava account first."
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
            
            # Handle authorization errors specifically
            if activity_response.status_code == 401 or activity_response.status_code == 403:
                error_detail = activity_response.text
                try:
                    error_json = activity_response.json()
                    error_detail = str(error_json)
                except:
                    pass
                print(f"ERROR: Strava authorization failed for activity {activity_id}: {error_detail}")
                print(f"DEBUG: Token length: {len(access_token) if access_token else 0}")
                raise HTTPException(
                    status_code=401,
                    detail=f"Strava authorization failed. The access token may be invalid or expired. Please reconnect your Strava account. Error: {error_detail}"
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
        elif e.response.status_code == 401 or e.response.status_code == 403:
            error_detail = e.response.text
            try:
                error_json = e.response.json()
                error_detail = str(error_json)
            except:
                pass
            raise HTTPException(
                status_code=401,
                detail=f"Strava authorization failed. Please reconnect your Strava account. Error: {error_detail}"
            )
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
