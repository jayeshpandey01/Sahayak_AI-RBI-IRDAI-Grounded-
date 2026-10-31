# Deploy Sahayak AI on Vercel

The repository is configured as two Vercel projects because the web client is
an Expo static export and the API is a FastAPI service:

1. **Web project:** repository root, using the root `vercel.json`.
2. **API project:** same GitHub repository, with Vercel's **Root Directory** set
   to `backend`. Vercel detects `main.py` as the FastAPI entry point.

This publishes the browser build and API. Android and iOS remain native app
builds and are not hosted by Vercel.

## 1. Create a persistent PostgreSQL database

Use managed PostgreSQL and its pooled connection URL. Vercel functions have an
ephemeral, read-only filesystem outside `/tmp`; local SQLite is not suitable
for persistent production data.

Before deploying the API for the first time, point both database variables to
the new database in a secure shell and run the one-time bootstrap from the
repository root:

```sh
cd backend
python -m pip install -r requirements.txt
export DATABASE_URL='postgresql://...'
export SYNC_DATABASE_URL="$DATABASE_URL"
python scripts/bootstrap_vercel_db.py
```

The bootstrap refuses SQLite and databases that already contain tables. It
creates the schema from the current SQLAlchemy models. It is for a new empty
database only; it is not an upgrade tool for existing deployments.

## 2. Deploy the API project

Import the GitHub repository into Vercel and set **Root Directory** to
`backend`. Add these environment variables to the API project for Production:

- `ENVIRONMENT=production`
- `DATABASE_URL`: pooled PostgreSQL connection URL bootstrapped above
- `JWT_SECRET`: a stable, randomly generated secret
- `ALLOWED_ORIGINS`: exact HTTPS origin of the web project, for example
  `https://your-web-project.vercel.app`
- `STRIPE_MODE=test` for test-only checkout; add test Stripe keys only if you
  want to exercise that feature
- To enable external AI, set `AI_EXTERNAL_PROCESSING_ENABLED=true`,
  `AI_REAL_USER_ROLLOUT_APPROVED=true`, a provider key, and
  `AI_RATE_LIMIT_HMAC_KEY`; otherwise leave external AI disabled
- Email provider keys only if password-reset email delivery is required

Production startup rejects SQLite, requires HTTPS origins and a stable JWT
secret, and fails if expected application tables are missing. Swagger UI is at
`https://<api-domain>/docs`, ReDoc at `https://<api-domain>/redoc`, and the
OpenAPI schema at `https://<api-domain>/openapi.json`. Use the Swagger
**Authorize** control with a bearer token for protected endpoints.

After deploying, verify `https://<api-domain>/health` reports `healthy`.

## 3. Deploy the Expo web client

Create a second Vercel project from the same repository with the repository root
as its root directory. Configure this build environment variable:

- `EXPO_PUBLIC_API_BASE_URL=https://<api-domain>`

The web build exports the Expo app to `dist` and fails early if the API URL is
missing or is not HTTPS. Set the API's `ALLOWED_ORIGINS` to the web project's
final HTTPS origin, then redeploy the API if needed.

## Operational limits

- Keep the database and API in nearby regions and use a pooled PostgreSQL URL.
- Large document uploads may exceed Vercel's function request body limit; use
  object storage for production file uploads.
- The existing SQL files in `backend/migrations/` are not the bootstrap path
  for a fresh Vercel PostgreSQL deployment. Schema upgrades after initial
  bootstrap need proper versioned PostgreSQL migrations before deploying app
  changes that require new columns or tables.
- Wallet funding/transfers and loan records remain demo/simulated features.
  This deployment setup does not enable real lending or money movement.

## Local web build check

```sh
EXPO_PUBLIC_API_BASE_URL=https://api.example.vercel.app npm run vercel:build
```
