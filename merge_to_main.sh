#!/bin/bash
# Script to safely merge feature/strava-oauth to main

echo "🔄 Merging feature/strava-oauth to main..."
echo ""

# Check if on feature branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "feature/strava-oauth" ]; then
    echo "⚠️  Warning: Not on feature/strava-oauth branch (currently on $CURRENT_BRANCH)"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  Warning: You have uncommitted changes"
    git status --short
    read -p "Commit changes first? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add -A
        git commit -m "WIP: Uncommitted changes before merge"
    else
        echo "Aborting merge"
        exit 1
    fi
fi

# Switch to main
echo "📦 Switching to main branch..."
git checkout main

# Pull latest main
echo "⬇️  Pulling latest main..."
git pull origin main

# Merge feature branch
echo "🔀 Merging feature/strava-oauth..."
git merge feature/strava-oauth --no-ff -m "Merge feature/strava-oauth: Add Strava OAuth integration and multi-activity analysis"

# Check for conflicts
if [ $? -ne 0 ]; then
    echo "❌ Merge conflicts detected! Please resolve manually."
    exit 1
fi

echo ""
echo "✅ Merge successful!"
echo ""
echo "Next steps:"
echo "1. Test the merged code: python3 -m uvicorn backend.main:app --reload"
echo "2. If everything works: git push origin main"
echo "3. Deploy to Render.com"
