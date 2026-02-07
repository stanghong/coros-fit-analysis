# Testing Checklist for Strava OAuth Feature

## Pre-Merge Testing (on feature/strava-oauth branch)

### ✅ Basic Functionality
- [ ] Server starts without errors
- [ ] Dashboard loads correctly
- [ ] Strava tab appears when `STRAVA_ENABLED=true`
- [ ] Strava tab hidden when `STRAVA_ENABLED=false`

### ✅ Strava OAuth Flow
- [ ] "Connect Strava" button redirects to Strava
- [ ] Authorization completes successfully
- [ ] Redirect back to dashboard works
- [ ] Connection status shows correctly

### ✅ Activity Import
- [ ] "Load Activities" fetches activities from Strava
- [ ] Only swimming activities are shown
- [ ] Activity list displays correctly with checkboxes
- [ ] Activity details (name, distance, date) are correct

### ✅ Single Activity Analysis
- [ ] "Analyze" button works for individual activities
- [ ] Analysis results display correctly
- [ ] All charts render properly
- [ ] Coach summary shows for single activity

### ✅ Multiple Activity Comparison
- [ ] Can select 2-20 activities with checkboxes
- [ ] "Compare Selected" button appears when 2+ selected
- [ ] Comparison analysis completes successfully
- [ ] Multi-workout coach summary displays
- [ ] Time series charts render correctly
- [ ] Trends, insights, and recommendations show

### ✅ Error Handling
- [ ] Handles missing Strava credentials gracefully
- [ ] Handles expired tokens (shows reconnect message)
- [ ] Handles non-swimming activities (filters them out)
- [ ] Handles network errors gracefully

### ✅ Edge Cases
- [ ] Works with 0 activities
- [ ] Works with 1 activity (shows analyze button)
- [ ] Works with 2 activities (shows compare button)
- [ ] Works with 20 activities (max limit)
- [ ] Handles activities without stream data

## Post-Merge (on main branch)

### ✅ Deployment Readiness
- [ ] All environment variables documented
- [ ] README updated with Strava setup instructions
- [ ] No hardcoded credentials
- [ ] Feature flag works correctly

### ✅ Production Considerations
- [ ] Token storage (currently in-memory, needs DB for production)
- [ ] Session management (currently single-user, needs multi-user)
- [ ] Error logging configured
- [ ] Rate limiting considered (Strava API limits)

## Merge Command

Once all tests pass:
```bash
git checkout main
git merge feature/strava-oauth
git push origin main
```

## Rollback Plan

If issues found after merge:
```bash
git revert <merge-commit-hash>
git push origin main
```
