# Data Directory

This directory contains the DuckDB database file and its backups.

## Files

- `tournament_data.duckdb` - Main database file (automatically created on first import)
- `tournament_data.duckdb.backup*` - Database backups created before migrations or manual backups

## Database Location

The database is stored here to keep the project root clean and organize data files separately from code.

## Backups

Before any major database operation, create a backup:

```bash
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)
```

## Gitignore

Database files are excluded from git via `.gitignore` to prevent committing large binary files.
Only this README is tracked in version control.
