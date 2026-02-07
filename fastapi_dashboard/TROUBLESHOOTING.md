# Troubleshooting Guide

## Issue: Nothing happens when uploading CSV file

### Step 1: Check Browser Console
1. Open browser Developer Tools (F12 or Right-click → Inspect)
2. Go to **Console** tab
3. Try uploading a file
4. Look for any red error messages

**Common errors to look for:**
- `Failed to fetch` → Server not running or wrong URL
- `404 Not Found` → API endpoint not found
- `500 Internal Server Error` → Backend error (check server logs)
- JavaScript errors → Frontend code issue

### Step 2: Check Network Tab
1. In Developer Tools, go to **Network** tab
2. Try uploading a file
3. Look for a request to `/api/analyze`
4. Check:
   - **Status**: Should be 200 (green) or error code (red)
   - **Response**: Click on the request to see server response
   - **Request**: Check if file is being sent

### Step 3: Check Server Logs
Look at the terminal where you started the server. You should see:
```
Received file upload request: [filename]
File size: [bytes] bytes
CSV loaded: [rows] rows, [cols] columns
Starting analysis...
Analysis complete
Returning analysis results
```

If you see errors here, that's where the problem is.

### Step 4: Test the API Directly

Test if the server is responding:
```bash
curl http://localhost:8000/api/health
```

Should return: `{"status":"ok","message":"Swimming Dashboard API is running"}`

### Step 5: Common Issues

**Issue: Server not running**
- Solution: Start the server with `cd backend && python main.py`

**Issue: Port 8000 already in use**
- Solution: Change port in `main.py` or kill the process using port 8000

**Issue: CSV file format incorrect**
- Solution: Make sure it's a valid Coros CSV file with expected columns

**Issue: CORS errors**
- Solution: CORS middleware is already added, but check browser console

**Issue: JavaScript errors**
- Solution: Check browser console for specific error messages

### Step 6: Manual Test

You can test the API directly with curl:
```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "file=@csv_folder/swimming/455369450500161536.csv"
```

This will show you the raw JSON response and help identify if the issue is frontend or backend.

### Debugging Checklist

- [ ] Server is running (check terminal)
- [ ] Browser console shows no errors
- [ ] Network tab shows request being sent
- [ ] Server logs show file being received
- [ ] CSV file is valid format
- [ ] File size is reasonable (< 50MB)

### Getting Help

If still not working, provide:
1. Browser console errors (screenshot or copy text)
2. Server terminal output (copy text)
3. Network tab details (status code, response)
4. CSV file sample (first few rows)
