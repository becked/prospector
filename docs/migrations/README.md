# Database Migrations

This directory contains numbered migration documents that track schema changes to the DuckDB database.

## Migration Numbering

Migrations are numbered sequentially:
- `001_add_logdata_events.md`
- `002_add_history_tables.md`
- `003_add_rulers_table.md`
- etc.

## Migration Document Structure

Each migration document should include:

1. **Overview** - What is being changed and why
2. **Schema Changes** - DDL statements (CREATE TABLE, ALTER TABLE, etc.)
3. **Data Migration** - Any data transformation or backfill steps
4. **Validation** - How to verify the migration succeeded
5. **Rollback Procedure** - How to undo the migration if needed

## Running a Migration

Migrations in this project are applied by modifying the import scripts or database initialization code, then re-importing data.

### Standard Migration Workflow

```bash
# 1. Backup the database
cp data/tournament_data.duckdb data/tournament_data.duckdb.backup_$(date +%Y%m%d_%H%M%S)

# 2. Apply schema changes (modify import scripts or create migration script)
# Edit tournament_visualizer/parser.py or create a dedicated migration script

# 3. Re-import data (if needed)
uv run python scripts/import_attachments.py --directory saves --force --verbose

# 4. Run validation scripts
uv run python scripts/validate_logdata.py
uv run python scripts/validate_participants.py
# ... other relevant validation scripts

# 5. Update schema documentation
uv run python scripts/export_schema.py
git add docs/schema.sql docs/database-schema.md

# 6. Verify the changes
uv run duckdb data/tournament_data.duckdb -readonly -c "DESCRIBE new_table_name"
uv run python scripts/verify_analytics.py
```

## After Running a Migration

**Always update the schema documentation:**

```bash
# Export current schema to documentation
uv run python scripts/export_schema.py

# Commit the updated schema docs with your migration
git add docs/schema.sql docs/database-schema.md
git commit -m "docs: Update schema docs after migration XXX"
```

This ensures:
- The schema docs stay in sync with reality
- New developers can see the current schema
- Git history shows exactly what changed

## Creating a New Migration

1. **Create the migration document:**
   ```bash
   # Use the next sequential number
   touch docs/migrations/010_your_migration_name.md
   ```

2. **Document the changes:**
   - Explain the purpose
   - Show DDL statements
   - Document any data transformations
   - Provide rollback steps

3. **Apply the migration:**
   - Follow the standard workflow above
   - Test thoroughly before committing

4. **Update schema docs:**
   ```bash
   uv run python scripts/export_schema.py
   ```

5. **Commit everything:**
   ```bash
   git add docs/migrations/010_your_migration_name.md
   git add docs/schema.sql docs/database-schema.md
   git add tournament_visualizer/  # Any code changes
   git commit -m "feat: Add your migration description"
   ```

## Rollback Procedure

If a migration fails or needs to be reverted:

1. **Restore from backup:**
   ```bash
   cp data/tournament_data.duckdb.backup_YYYYMMDD_HHMMSS data/tournament_data.duckdb
   ```

2. **Revert code changes:**
   ```bash
   git revert <commit-hash>
   ```

3. **Update schema docs:**
   ```bash
   uv run python scripts/export_schema.py
   git add docs/schema.sql docs/database-schema.md
   git commit -m "docs: Update schema docs after rollback"
   ```

## Migration Best Practices

- **Always backup** before running migrations
- **Test on a copy** of the database first
- **Document everything** in the migration doc
- **Update schema docs** immediately after migration
- **Run all validation scripts** to verify correctness
- **Commit atomically** - migration doc + code + schema docs together

## See Also

- `docs/schema.sql` - Current database DDL
- `docs/database-schema.md` - Human-readable schema reference
- `scripts/export_schema.py` - Schema documentation generator
- `CLAUDE.md` - Database management commands
