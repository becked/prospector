# Pre-Deployment Checklist

Use this checklist before deploying to Fly.io to ensure everything is ready.

## Code Readiness

- [ ] All tests pass locally
  ```bash
  uv run pytest -v
  ```

- [ ] Code is formatted and linted
  ```bash
  uv run black tournament_visualizer/
  uv run ruff check tournament_visualizer/
  ```

- [ ] Git working directory is clean
  ```bash
  git status
  ```

- [ ] All changes are committed
  ```bash
  git log -1
  ```

## Local Testing

- [ ] App runs with development server
  ```bash
  uv run python manage.py start
  # Visit http://localhost:8050
  ```

- [ ] App runs with Gunicorn locally
  ```bash
  PORT=8080 uv run gunicorn "tournament_visualizer.app:server" --config gunicorn.conf.py
  # Visit http://localhost:8080
  ```

- [ ] Scripts work with environment variables
  ```bash
  export CHALLONGE_KEY="your_key"
  export CHALLONGE_USER="your_username"
  export challonge_tournament_id="your_tournament_id"
  uv run python scripts/download_attachments.py
  uv run python scripts/import_attachments.py --verbose
  ```

- [ ] Docker image builds successfully
  ```bash
  docker build -t tournament-visualizer:test .
  ```

- [ ] Docker container runs successfully
  ```bash
  docker run --rm -p 8080:8080 --env-file .env tournament-visualizer:test
  # Visit http://localhost:8080
  ```

## Fly.io Setup

- [ ] Fly.io CLI installed
  ```bash
  flyctl version
  ```

- [ ] Authenticated to Fly.io
  ```bash
  flyctl auth whoami
  ```

- [ ] App name chosen (must be globally unique)
  - Update `app = "..."` in `fly.toml`
  - Verify available: `flyctl apps create <name> --org personal`

- [ ] Region selected
  - Update `primary_region = "..."` in `fly.toml`
  - List regions: `flyctl platform regions`

## API Credentials

- [ ] Challonge API key obtained
  - Get from: https://challonge.com/settings/developer
  - Store securely (password manager)

- [ ] Challonge username confirmed
  - Your Challonge login username

- [ ] Tournament ID identified
  - Example: `oldworld1v1league` from URL `challonge.com/oldworld1v1league`

## Environment Variables

- [ ] `.env` file exists locally (for development)
  ```bash
  cat .env
  ```

- [ ] `.env` contains all required variables:
  - `CHALLONGE_KEY`
  - `CHALLONGE_USER`
  - `challonge_tournament_id`

- [ ] `.env` is in `.gitignore` (never commit secrets!)
  ```bash
  grep "^\.env$" .gitignore
  ```

## Configuration Files

- [ ] `fly.toml` reviewed and updated
  - App name is unique
  - Region is correct
  - Volume mount is configured
  - Health checks are appropriate

- [ ] `Dockerfile` is present and correct
  - Multi-stage build
  - Non-root user
  - Correct CMD

- [ ] `gunicorn.conf.py` is present
  - Worker count appropriate
  - Timeout set to 120s

- [ ] `.dockerignore` is present
  - Excludes .git, tests, docs
  - Excludes .env and sensitive files

## Documentation

- [ ] Deployment guide reviewed
  - `docs/deployment/flyio-deployment-guide.md`

- [ ] Implementation plan reviewed
  - `docs/plans/flyio-deployment-implementation-plan.md`

## First Deployment Only

- [ ] Volume created
  ```bash
  flyctl volumes create tournament_data --size 1 --region <region>
  ```

- [ ] Secrets set
  ```bash
  flyctl secrets set CHALLONGE_KEY="..."
  flyctl secrets set CHALLONGE_USER="..."
  flyctl secrets set challonge_tournament_id="..."
  ```

- [ ] Verify secrets
  ```bash
  flyctl secrets list
  ```

## Final Checks

- [ ] Recent backup of local database (if exists)
  ```bash
  cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d)
  ```

- [ ] README updated with deployment info (if needed)

- [ ] Team notified of deployment (if applicable)

## Deploy!

Once all checks pass:

```bash
# Deploy to Fly.io
flyctl deploy

# Watch logs during deployment
flyctl logs --follow

# Verify status
flyctl status

# Open in browser
flyctl open
```

## Post-Deployment Verification

After deployment completes:

- [ ] App is accessible via URL
  ```bash
  flyctl open
  ```

- [ ] All navigation links work
  - Overview page
  - Matches page
  - Players page
  - Maps page

- [ ] Data is present
  - Matches table shows data
  - Player statistics appear
  - No "No Data" messages

- [ ] No errors in logs
  ```bash
  flyctl logs --level error
  ```

- [ ] Health checks passing
  ```bash
  flyctl checks
  ```

## Rollback Plan

If deployment fails:

1. **View error logs**:
   ```bash
   flyctl logs --level error
   ```

2. **Check releases**:
   ```bash
   flyctl releases
   ```

3. **Rollback to previous version**:
   ```bash
   flyctl releases rollback <previous-version>
   ```

4. **Debug locally**:
   - Pull down the image: `flyctl ssh console`
   - Check files: `ls -la /app /data`
   - Run scripts manually

## Success Criteria

Deployment is successful when:

✅ Health checks are passing
✅ App loads in browser
✅ Data is visible (matches, players, etc.)
✅ Navigation works
✅ No errors in logs
✅ Response time is reasonable (<3 seconds)

## Notes

- First deployment takes 5-10 minutes (includes data import)
- Subsequent deployments take 2-5 minutes
- Volume persists across deployments
- Secrets persist (no need to reset)
