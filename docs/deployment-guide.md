# Fly.io Deployment Guide

Complete guide for deploying the Old World Tournament Visualizer to Fly.io.

## Prerequisites

1. **Fly.io account** - Sign up at https://fly.io
2. **flyctl installed** - Install from https://fly.io/docs/hands-on/install-flyctl/
3. **Authentication** - Run `fly auth login`
4. **Challonge API credentials**:
   - API key from https://challonge.com/settings/developer
   - Your Challonge username
   - Tournament ID you want to track

## Initial Deployment (First Time)

### 1. Launch the App

From the project root directory:

```bash
fly launch
```

This will:
- Detect the Dockerfile and build configuration
- Read `fly.toml` for app settings
- Prompt you to choose a name (default: `prospector`)
- Prompt you to choose a region (e.g., `sjc` for San Jose)
- **IMPORTANT:** When asked "Would you like to set up a Postgresql database?", answer **NO**
- **IMPORTANT:** When asked "Would you like to deploy now?", answer **NO** (we need to create the volume first)

### 2. Create the Persistent Volume

The app needs a persistent volume for the DuckDB database and save files:

```bash
fly volumes create tournament_data --size 1 --region sjc -a prospector
```

Notes:
- Volume name must match `fly.toml`: `tournament_data`
- Region must match your app region
- Size is 1GB (can expand later with `fly volumes extend`)
- Replace `prospector` with your actual app name

Verify the volume was created:
```bash
fly volumes list -a prospector
```

### 3. Set Environment Secrets

Configure the Challonge API credentials as secrets:

```bash
fly secrets set \
  CHALLONGE_KEY="your_api_key_here" \
  CHALLONGE_USER="your_username_here" \
  challonge_tournament_id="your_tournament_id" \
  -a prospector
```

Verify secrets are set (values will be redacted):
```bash
fly secrets list -a prospector
```

### 4. Deploy the Application

Now deploy for the first time:

```bash
fly deploy
```

This will:
- Build the Docker image
- Push to Fly.io registry
- Create and start the app
- Map to `https://prospector.fly.dev`

Monitor the deployment:
```bash
fly logs -a prospector
```

### 5. Initial Data Sync

After first deployment, sync the tournament data:

```bash
./scripts/sync_tournament_data.sh prospector
```

This will:
1. Download save files from Challonge
2. Import them into DuckDB
3. Restart the app

### 6. Verify Deployment

Check that everything is working:

```bash
# Check app status
fly status -a prospector

# View logs
fly logs -a prospector

# Open in browser
fly open -a prospector
```

The app should show tournament data on the Overview page.

## Subsequent Deployments

After the initial deployment, deploying updates is simple:

### Deploy Code Changes

```bash
fly deploy
```

That's it! Fly.io will:
- Build the new image
- Deploy with zero downtime (creates new VM, switches traffic, removes old VM)
- Your data persists in the volume

### Update Tournament Data

After matches are uploaded to Challonge:

```bash
./scripts/sync_tournament_data.sh
```

This updates the production database without redeploying code.

## Configuration Management

### Update Secrets

Change environment variables:

```bash
fly secrets set CHALLONGE_KEY="new_key" -a prospector
```

This automatically restarts the app.

### View Current Configuration

```bash
# View fly.toml settings
cat fly.toml

# View secrets (redacted values)
fly secrets list -a prospector

# View app info
fly info -a prospector

# View volume info
fly volumes list -a prospector
```

### Scale Resources

If you need more memory or CPU:

```bash
# View current scaling
fly scale show -a prospector

# Increase memory to 2GB
fly scale memory 2048 -a prospector

# Increase volume size to 2GB
fly volumes extend <volume-id> --size 2 -a prospector
```

Get volume ID with `fly volumes list -a prospector`.

## Troubleshooting

### Check Application Logs

```bash
# Recent logs
fly logs -a prospector

# Follow logs (live)
fly logs -a prospector --tail

# Last 200 lines
fly logs -a prospector --lines 200
```

### SSH into Running Container

For debugging:

```bash
fly ssh console -a prospector
```

Once inside, you can:
- Check disk space: `df -h`
- View files: `ls -lh /data`
- Check database: `python -c "import duckdb; print(duckdb.connect('/data/tournament_data.duckdb').execute('SELECT COUNT(*) FROM matches').fetchone())"`
- View environment: `env | grep CHALLONGE`

Exit with `exit`.

### Restart the App

If the app is misbehaving:

```bash
fly apps restart prospector
```

### Check Health Status

```bash
# View overall status
fly status -a prospector

# Check health endpoint
curl https://prospector.fly.dev/health
```

### Common Issues

#### 1. "Volume not found" during deployment

**Problem:** Volume wasn't created before first deploy.

**Solution:**
```bash
fly volumes create tournament_data --size 1 --region sjc -a prospector
fly deploy
```

#### 2. Database shows "No Data"

**Problem:** Haven't synced tournament data yet.

**Solution:**
```bash
./scripts/sync_tournament_data.sh
```

#### 3. "Permission denied" errors in logs

**Problem:** Volume permissions issue.

**Solution:**
```bash
fly ssh console -a prospector
# Inside the container:
chown -R appuser:appuser /data
exit
fly apps restart prospector
```

#### 4. App won't start (502 errors)

**Problem:** App is crashing, likely due to missing secrets.

**Solution:**
```bash
# Check logs for specific error
fly logs -a prospector

# Verify secrets are set
fly secrets list -a prospector

# If missing, set them:
fly secrets set CHALLONGE_KEY="key" CHALLONGE_USER="user" challonge_tournament_id="id" -a prospector
```

#### 5. "Out of memory" errors

**Problem:** 1GB RAM is insufficient for large tournaments.

**Solution:**
```bash
# Increase to 2GB
fly scale memory 2048 -a prospector
```

#### 6. Slow queries / timeouts

**Problem:** Complex analytics queries taking too long.

**Solution:** Already configured with 120s timeout in gunicorn. If still timing out:
```bash
# Increase timeout via environment variable
fly secrets set GUNICORN_TIMEOUT="180" -a prospector
```

Then update `gunicorn.conf.py` to use this variable.

## Monitoring

### View Metrics

```bash
# View metrics dashboard
fly dashboard -a prospector
```

Or visit: https://fly.io/dashboard/<your-org>/prospector

### Set Up Alerts

In the Fly.io dashboard, you can configure alerts for:
- App crashes
- High memory usage
- Health check failures
- Certificate expiration

## Costs

Current configuration costs:
- **Compute**: Shared CPU, 1GB RAM (~$3-5/month)
- **Volume**: 1GB persistent storage (~$0.15/month)
- **Bandwidth**: First 100GB free

Monitor costs at: https://fly.io/dashboard/<your-org>/billing

## Cleanup / Deletion

To completely remove the app:

```bash
# Delete the app (includes VMs)
fly apps destroy prospector

# Volume is automatically deleted with the app
# Or delete manually if needed:
fly volumes delete <volume-id> -a prospector
```

**WARNING:** This permanently deletes all data!

## Additional Resources

- Fly.io Documentation: https://fly.io/docs/
- Fly.io Status: https://status.flyio.net/
- Support: https://community.fly.io/

## Next Steps

After deployment:
1. Set up a custom domain (optional): `fly domains add yourdomain.com -a prospector`
2. Enable auto-scaling (if needed): `fly autoscale set min=1 max=3 -a prospector`
3. Schedule regular data syncs (e.g., via cron on your local machine)
4. Set up monitoring alerts in the Fly.io dashboard
