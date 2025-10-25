# Implementation Plan Validation Checklist

Use this checklist to determine if an implementation plan should be archived.

## For Each Plan

Plan file: `_______________________________`

### Completion Checks

- [ ] Feature is documented in CLAUDE.md (section: _____________)
- [ ] Code exists in codebase (files: _____________)
- [ ] Tests exist (files: _____________)
- [ ] Migration doc created (if applicable): migrations/_____.md
- [ ] Feature works in current app (manual test: _____________)

### Decision

- [ ] **Archive** - All checks pass, feature is complete
- [ ] **Keep Active** - Work is ongoing or planned
- [ ] **Delete** - Obsolete/superseded by different approach

### Archive Notes

If archiving, add brief note at top of plan:

```markdown
> **Status**: Completed and archived (YYYY-MM-DD)
>
> This feature is now documented in CLAUDE.md (section: <name>).
> See migrations/XXX.md for schema changes.
```
