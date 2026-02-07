# Troubleshooting Guide

## Common Issues and Solutions

### Import Errors

**Error: "Could not import module 'app'"**

This usually happens when running uvicorn from the wrong directory or with incorrect module path.

**Solution:**
- If running from `fastapi_dashboard/` directory:
  ```bash
  uvicorn backend.main:app --reload
  ```
- If running from `fastapi_dashboard/backend/` directory:
  ```bash
  uvicorn main:app --reload
  ```
- Or use the start script:
  ```bash
  ./start.sh
  ```

**Error: "ModuleNotFoundError: No module named 'strava_oauth'"**

This happens when `STRAVA_ENABLED=true` but the module can't be imported.

**Solution:**
- Make sure you're running from the correct directory
- Check that `fastapi_dashboard/backend/strava_oauth.py` exists
- If Strava is not needed, set `STRAVA_ENABLED=false`

### Port Already in Use

**Error: "Address already in use"**

**Solution:**
- Change the port in `backend/main.py`:
  ```python
  uvicorn.run(app, host="0.0.0.0", port=8001)  # Use port 8001
  ```
- Or kill the process using port 8000:
  ```bash
  lsof -ti:8000 | xargs kill -9
  ```

### File Upload Not Working

**Issues:**
- File not uploading
- "No file selected" error
- Analysis fails

**Solutions:**
- Check that the file is a valid CSV
- Ensure the CSV has the expected Coros format columns
- Check browser console for errors
- Verify file size is reasonable (< 10MB)

### Strava Integration Issues

**Error: "Strava OAuth not configured"**

**Solution:**
- Set `STRAVA_ENABLED=false` if you don't need Strava
- Or configure Strava credentials:
  - `STRAVA_CLIENT_ID`
  - `STRAVA_CLIENT_SECRET`
  - `STRAVA_REDIRECT_URI`

**Error: "httpx library not installed"**

**Solution:**
```bash
pip install httpx
```

### Chart Display Issues

**Charts not showing:**
- Check browser console for JavaScript errors
- Ensure Chart.js is loaded (check network tab)
- Verify data is being returned from API

### Mobile Display Issues

**Charts too small or cut off:**
- Clear browser cache
- Check that latest version is deployed
- Verify responsive CSS is loaded

## Development Tips

### Running Locally

1. **From fastapi_dashboard directory:**
   ```bash
   cd fastapi_dashboard
   ./start.sh
   ```

2. **Or manually:**
   ```bash
   cd fastapi_dashboard
   python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **From backend directory:**
   ```bash
   cd fastapi_dashboard/backend
   python3 main.py
   ```

### Testing Strava Integration

1. Set environment variables:
   ```bash
   export STRAVA_ENABLED=true
   export STRAVA_CLIENT_ID=your_id
   export STRAVA_CLIENT_SECRET=your_secret
   export STRAVA_REDIRECT_URI=http://localhost:8000/strava/callback
   ```

2. Start server and test OAuth flow

### Debugging

- Check server logs for errors
- Use browser developer tools (F12) to see console errors
- Verify API responses in Network tab
- Check that environment variables are set correctly
