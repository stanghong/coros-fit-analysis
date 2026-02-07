# Deployment Guide for Render.com

This guide will help you deploy the Swimming Workout Dashboard to Render.com.

## Prerequisites

- GitHub account with the repository pushed
- Render.com account (free tier available)

## Step-by-Step Deployment

### Step 1: Sign up / Log in to Render

1. Go to [https://render.com](https://render.com)
2. Sign up or log in (you can use GitHub to sign in)

### Step 2: Create a New Web Service

1. Click **"New +"** button in the dashboard
2. Select **"Web Service"**
3. Connect your GitHub account if not already connected
4. Select the repository: `stanghong/coros-fit-analysis`

### Step 3: Configure the Service

Use these settings:

**Basic Settings:**
- **Name**: `swimming-workout-dashboard` (or any name you prefer)
- **Region**: Choose closest to you (e.g., `Oregon (US West)`)
- **Branch**: `main`
- **Root Directory**: `fastapi_dashboard`

**Build & Deploy:**
- **Environment**: `Python 3`
- **Build Command**: 
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**: 
  ```bash
  uvicorn backend.main:app --host 0.0.0.0 --port $PORT
  ```

**Advanced Settings (optional):**
- **Python Version**: `3.12.0` (or latest available)
- **Auto-Deploy**: `Yes` (deploys on every push to main)

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will start building your application
3. Wait for the build to complete (usually 2-5 minutes)
4. Once deployed, you'll get a URL like: `https://swimming-workout-dashboard.onrender.com`

### Step 5: Verify Deployment

1. Visit your Render URL
2. You should see the Swimming Workout Dashboard
3. Test by uploading a CSV file

## Environment Variables (Optional)

If you need any environment variables later, you can add them in:
- Render Dashboard → Your Service → Environment

## Troubleshooting

### Build Fails

- Check the build logs in Render dashboard
- Ensure `requirements.txt` is in the `fastapi_dashboard/` directory
- Verify Python version compatibility

### App Crashes on Start

- Check the logs in Render dashboard
- Ensure the start command is correct
- Verify the PORT environment variable is being used

### File Upload Issues

- Render has file size limits on free tier
- Check that uploads directory has write permissions
- Verify CORS settings if accessing from different domain

## Updating Your Deployment

Every time you push to the `main` branch, Render will automatically:
1. Pull the latest code
2. Rebuild the application
3. Deploy the new version

You can also manually trigger a deploy from the Render dashboard.

## Free Tier Limitations

- Services spin down after 15 minutes of inactivity
- First request after spin-down may take 30-60 seconds
- 750 hours/month free (enough for always-on for ~1 month)
- Upgrade to paid plan for always-on service

## Custom Domain (Optional)

1. Go to your service settings
2. Click "Custom Domains"
3. Add your domain
4. Follow DNS configuration instructions

## Support

If you encounter issues:
1. Check Render logs: Dashboard → Your Service → Logs
2. Check application logs in the service
3. Review Render documentation: https://render.com/docs
