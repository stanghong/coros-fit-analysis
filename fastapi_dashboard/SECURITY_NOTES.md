# Security Notes

This document captures security defaults and production hardening expectations for the FastAPI dashboard.

## 1) Runtime mode (`ENV`)

- `ENV=dev`
  - Enables development-only behavior.
  - Dev debug endpoints are available.
  - In-memory Strava token fallback is allowed (for local testing only).

- `ENV=prod` (or any non-`dev` value)
  - Debug endpoints are disabled (return 404).
  - In-memory token fallback is disabled.
  - Strava OAuth requires database persistence.

## 2) CORS (`CORS_ALLOW_ORIGINS`)

Set an explicit allowlist in production:

```bash
CORS_ALLOW_ORIGINS=https://app.example.com,https://admin.example.com
```

Notes:
- Do **not** use wildcard (`*`) with credentialed requests.
- In dev, localhost defaults are used if `CORS_ALLOW_ORIGINS` is unset.
- In production, unset `CORS_ALLOW_ORIGINS` results in no allowed origins.

## 3) Debug endpoints

The following endpoints are development-only:
- `/debug/strava-athlete`
- `/strava/debug/strava-athlete`

They are automatically gated by `ENV=dev`.

## 4) Token storage policy

Production requires DB-backed token storage.

- If DB persistence fails during Strava OAuth callback in production, the callback fails with 503.
- If database is unavailable in production, Strava OAuth is rejected with 503.

This prevents accidental single-user in-memory token behavior in production.

## 5) Logging guidance

- Avoid logging OAuth authorization codes and token values.
- Keep detailed OAuth debug logging limited to `ENV=dev`.
- If additional debug logs are introduced, ensure secrets are redacted.
