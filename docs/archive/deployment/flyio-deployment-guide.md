# Fly.io Deployment Guide

This guide covers deploying the Old World Tournament Visualizer to Fly.io.

## Prerequisites

1. **Fly.io Account**: Sign up at https://fly.io/
2. **Fly CLI**: Install flyctl
   ```bash
   # macOS
   brew install flyctl

   # Linux
   curl -L https://fly.io/install.sh | sh

   # Windows
   iwr https://fly.io/install.ps1 -useb | iex
   ```

3. **Fly.io Authentication**:
   ```bash
   flyctl auth login
   ```

4. **Challonge API Credentials**:
   - API Key: Get from https://challonge.com/settings/developer
   - Username: Your Challonge username
   - Tournament ID: The tournament to track

## First-Time Deployment

### Step 1: Launch the App

```bash
# Launch app (creates app on Fly.io)
flyctl launch --no-deploy

# Answer prompts:
# - App name: prospector (or your choice)
# - Region: Choose closest to your users
# - Postgres database: No
# - Redis: No
```

This creates the app but doesn't deploy yet (we need to set secrets first).

### Step 2: Create Volume for Persistent Storage

```bash
# Create 1GB volume for database and save files
flyctl volumes create tournament_data --size 1 --region sjc

# Verify volume was created
flyctl volumes list
```

**Important**: The volume must be in the same region as your app.

### Step 3: Set Environment Secrets

```bash
# Set Challonge API credentials
flyctl secrets set CHALLONGE_KEY="your_api_key_here"
flyctl secrets set CHALLONGE_USER="your_username"
flyctl secrets set challonge_tournament_id="your_tournament_id"

# Verify secrets are set (values are hidden)
flyctl secrets list
```

**Never commit these values to git!**

### Step 4: Deploy

```bash
# Deploy the application
flyctl deploy

# This will:
# 1. Build Docker image
# 2. Push to Fly.io registry
# 3. Run release command (download + import data)
# 4. Start the app
# 5. Run health checks
```

**First deployment takes 5-10 minutes** due to:
- Docker image build (~2-3 minutes)
- Data download (~1-2 minutes)
- Data import (~2-5 minutes)

### Step 5: Verify Deployment

```bash
# Check app status
flyctl status

# View logs
flyctl logs

# Open in browser
flyctl open
```

Expected status: All instances should show "started" and health checks passing.

## Subsequent Deployments

After initial setup, deployments are simpler:

```bash
# Make code changes
git add .
git commit -m "your changes"

# Deploy
flyctl deploy

# Watch logs during deployment
flyctl logs --follow
```

## Managing the Application

### View Logs

```bash
# Recent logs
flyctl logs

# Follow logs (live tail)
flyctl logs --follow

# Filter by severity
flyctl logs --level error
```

### Scale Resources

**Change Memory**:
```bash
# Scale to 1GB RAM (recommended for busy sites)
flyctl scale memory 1024

# Scale to 512MB RAM (minimum recommended)
flyctl scale memory 512
```

**Change Region**:
```bash
# Add instance in another region
flyctl scale count 2 --region lax
```

### Access Database

To inspect the DuckDB database:

```bash
# SSH into the running instance
flyctl ssh console

# Once inside:
cd /data
duckdb tournament_data.duckdb -readonly

# Example queries:
.tables
SELECT COUNT(*) FROM matches;
SELECT * FROM players LIMIT 10;

# Exit duckdb: Ctrl+D
# Exit SSH: exit
```

### Manual Data Refresh

If you need to refresh data without deploying:

```bash
# SSH into instance
flyctl ssh console

# Run scripts manually
cd /app
uv run python scripts/download_attachments.py
uv run python scripts/import_attachments.py --directory /data/saves --verbose

# Exit
exit
```

### Restart Application

```bash
# Restart all instances
flyctl apps restart prospector
```

## Troubleshooting

### App Won't Start

**Check logs**:
```bash
flyctl logs --level error
```

**Common issues**:
1. **Missing secrets**: Verify with `flyctl secrets list`
2. **Volume not mounted**: Check `flyctl volumes list`
3. **Import failed**: Check logs during release command
4. **Out of memory**: Scale to 1GB with `flyctl scale memory 1024`

### Release Command Fails

The release command runs before deployment completes. If it fails:

```bash
# View release command logs
flyctl releases --image

# SSH and run manually
flyctl ssh console
uv run python scripts/download_attachments.py
uv run python scripts/import_attachments.py --directory /data/saves --verbose
```

### Health Checks Failing

```bash
# Check health check status
flyctl status

# Common fixes:
# 1. Increase timeout in fly.toml http_checks.timeout
# 2. Check app actually runs on port 8080
# 3. Verify /data volume is mounted
```

### Database Corruption

If DuckDB database gets corrupted:

```bash
# SSH into instance
flyctl ssh console

# Backup existing database
cd /data
cp tournament_data.duckdb tournament_data.duckdb.backup

# Remove corrupted database
rm tournament_data.duckdb

# Re-import from saves
cd /app
uv run python scripts/import_attachments.py --directory /data/saves --force --verbose

# Exit
exit
```

## Monitoring

### View Metrics

```bash
# Resource usage
flyctl metrics

# App status
flyctl status

# Health checks
flyctl checks
```

### Set Up Alerts (Optional)

Fly.io can send alerts when:
- Health checks fail
- App crashes
- High resource usage

Configure at: https://fly.io/dashboard/personal/monitoring

## Costs

Typical monthly costs (as of 2025):
- **shared-cpu-1x @ 512MB**: ~$3.88/month
- **shared-cpu-1x @ 1GB**: ~$7.76/month
- **Volume (1GB)**: ~$0.15/month
- **Bandwidth**: Usually free tier (160GB/month)

**Total**: ~$4-8/month

Monitor usage: https://fly.io/dashboard/personal/billing

## Backup Strategy

### Automated Backups (Recommended)

Use Fly.io snapshots:

```bash
# Enable daily snapshots (costs ~$0.05/snapshot/month)
flyctl volumes create tournament_data_backup --snapshot-id <volume-snapshot-id>
```

### Manual Backups

```bash
# SSH into instance
flyctl ssh console

# Create backup
cd /data
tar -czf backup-$(date +%Y%m%d).tar.gz tournament_data.duckdb saves/

# Download to local machine (from local terminal)
flyctl ssh sftp get /data/backup-20251011.tar.gz ./backups/

# Exit SSH
exit
```

## Updating Configuration

### Update fly.toml

1. Edit `fly.toml` locally
2. Deploy: `flyctl deploy`

### Update Environment Variables

```bash
# Update a secret
flyctl secrets set CHALLONGE_KEY="new_key_value"

# Note: This triggers a restart
```

### Update Gunicorn Config

1. Edit `gunicorn.conf.py`
2. Commit changes
3. Deploy: `flyctl deploy`

## Destroying the App

**Warning**: This deletes everything including volumes!

```bash
# Delete app and all resources
flyctl apps destroy prospector

# You'll be prompted to confirm
```

## Additional Resources

- Fly.io Documentation: https://fly.io/docs/
- Fly.io Status: https://status.flyio.net/
- Community Forum: https://community.fly.io/
- Discord: https://fly.io/discord

## Getting Help

1. **Check logs first**: `flyctl logs --level error`
2. **Check Fly.io status**: https://status.flyio.net/
3. **Community forum**: https://community.fly.io/
4. **Project issues**: Create issue in this repo
