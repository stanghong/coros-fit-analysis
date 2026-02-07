# Quick Start Guide

## Option 1: Using the Start Script (Easiest)

```bash
cd fastapi_dashboard
./start.sh
```

## Option 2: Manual Start

1. **Navigate to the dashboard directory:**
```bash
cd fastapi_dashboard
```

2. **Install dependencies (if not already installed):**
```bash
pip install -r requirements.txt
```

3. **Start the server:**
```bash
cd backend
python main.py
```

4. **Open your browser:**
```
http://localhost:8000
```

## Testing with a Sample File

You can test the application with any CSV file from your `csv_folder/swimming/` directory:

1. Start the server (see above)
2. Open http://localhost:8000 in your browser
3. Click "Choose File" or drag and drop a CSV file
4. View the analysis results!

## Troubleshooting

### Port 8000 already in use?
Change the port in `backend/main.py`:
```python
uvicorn.run(app, host="0.0.0.0", port=8001)  # Use port 8001
```

### Import errors?
Make sure you're running from the `backend/` directory or adjust the Python path.

### File upload not working?
- Check that the file is a valid CSV
- Ensure the CSV has the expected Coros format columns
- Check browser console for errors

## Features

✅ Upload CSV workout files
✅ Automatic analysis and scoring
✅ Interactive charts (Speed over Time, Stroke Rate vs Speed)
✅ Pros & Cons feedback
✅ Next workout prescription
✅ Beautiful, responsive UI

Enjoy analyzing your swimming workouts! 🏊
