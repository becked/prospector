# Documentation Guide

Welcome! This guide helps you navigate the tournament visualizer documentation.

## Start Here

**New to the project?** Read these in order:

1. **[Developer Guide](developer-guide.md)** - Architecture, development workflow, database operations
2. **[Deployment Guide](deployment-guide.md)** - How to deploy to Fly.io
3. **[CLAUDE.md](../CLAUDE.md)** - Project conventions and feature documentation

## Active Documentation

### Essential Guides
- **[developer-guide.md](developer-guide.md)** - Core development reference (architecture, database, testing)
- **[deployment-guide.md](deployment-guide.md)** - Production deployment on Fly.io

### Schema & Structure
- **[migrations/](migrations/)** - Database schema changes (historical record, all relevant)
  - Numbered sequentially (001, 002, etc.)
  - Each documents a specific schema change
  - Read these to understand database evolution
- **[reference/](reference/)** - Technical specifications
  - `save-file-format.md` - Old World save file XML structure

### Unresolved Items
- **[issues/](issues/)** - Active issues requiring attention
- **[bugs/](bugs/)** - Known bugs under investigation

## Historical Context (Archive)

The `archive/` directory contains **completed** work and **historical** snapshots.

**When to look here:**
- Understanding why a decision was made
- Learning how a feature was implemented
- Historical context for current architecture

**What's archived:**
- **[archive/plans/](archive/plans/)** - Completed implementation plans
- **[archive/reports/](archive/reports/)** - Analysis and investigation reports
- **[archive/issues/](archive/issues/)** - Resolved issues
- **[archive/code-reviews/](archive/code-reviews/)** - Point-in-time code reviews
- **[archive/deployment/](archive/deployment/)** - Old deployment docs

**Note:** If a feature is working and documented in CLAUDE.md, its implementation plan is likely archived.

## Documentation Lifecycle

We follow this lifecycle to keep docs current:

### Active Documentation
- Living documents that reflect current state
- Updated as code changes
- Examples: developer-guide.md, CLAUDE.md, migrations/

### Planning Documents
- Implementation plans live in `plans/` during development
- Once feature is complete and documented in CLAUDE.md, move to `archive/plans/`
- Include pointer to relevant CLAUDE.md section

### Issue Tracking
- Issues live in `issues/` while unresolved
- Once resolved, move to `archive/issues/` with resolution notes

### Reports & Analysis
- Point-in-time investigations and analysis
- Usually archived after decisions are implemented
- Preserved for historical context

## Finding Information

**"How do I develop this app?"**
→ Read [developer-guide.md](developer-guide.md)

**"How do I deploy?"**
→ Read [deployment-guide.md](deployment-guide.md)

**"What are the project conventions?"**
→ Read [../CLAUDE.md](../CLAUDE.md)

**"How does feature X work?"**
→ Check [../CLAUDE.md](../CLAUDE.md) first, then [developer-guide.md](developer-guide.md)

**"Why was this designed this way?"**
→ Check [archive/plans/](archive/plans/) or [archive/reports/](archive/reports/)

**"What changed in the database?"**
→ Read [migrations/](migrations/) in order

**"Where's the save file format?"**
→ [reference/save-file-format.md](reference/save-file-format.md)

## Contributing to Documentation

When working on features:

1. **Create implementation plan** in `plans/` during development
2. **Document in CLAUDE.md** when feature is complete
3. **Archive implementation plan** to `archive/plans/`
4. **Update developer-guide.md** if architecture changes
5. **Create migration doc** if schema changes

See [../CLAUDE.md](../CLAUDE.md) for commit message conventions and development principles.
