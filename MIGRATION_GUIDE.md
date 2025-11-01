# Database Migration Guide

This guide explains how to migrate your production database to use the new foreign key relationship between `patients` and `health_records` tables.

## Overview

The migration changes the `health_records` table from storing patient names directly (`patient TEXT`) to using a foreign key reference (`patient_id INTEGER` referencing `patients(id)`).

**Migration runs automatically** when the bot starts up, but you can also run it manually for better control and visibility.

## Automatic Migration (Default Behavior)

The migration runs automatically when:
- The bot starts up and initializes the database
- A `Database` instance is created

This is safe and idempotent - it won't run if the database is already migrated.

## Manual Migration (Recommended for Production)

For production databases, we recommend running the migration manually first to:
1. Check migration status
2. Create a backup
3. Verify the migration completes successfully
4. Review any issues before starting the bot

### Step 1: Check Migration Status

```bash
# Check if migration is needed
python migrate_db.py --status

# Or specify a custom database path
python migrate_db.py --status --db-path /path/to/your/health_bot.db
```

This will show:
- Current database state
- Whether migration is needed
- How many records and patients will be affected

### Step 2: Create Backup (CRITICAL!)

**Always backup your production database before migration:**

```bash
# Create backup and show status
python migrate_db.py --backup --status

# The backup will be saved as: data/health_bot.db.backup_YYYYMMDD_HHMMSS
```

Or manually:
```bash
cp data/health_bot.db data/health_bot.db.backup_$(date +%Y%m%d_%H%M%S)
```

### Step 3: Dry Run (Optional but Recommended)

Test the migration without making changes:

```bash
python migrate_db.py --dry-run
```

This shows what would be migrated without actually changing the database.

### Step 4: Run Migration

```bash
# Run migration with backup
python migrate_db.py --backup

# Or without automatic backup (if you backed up manually)
python migrate_db.py
```

### Step 5: Verify Migration

Check that migration completed successfully:

```bash
python migrate_db.py --status
```

You should see: `✅ Database is already migrated!`

## Migration Process Details

The migration:
1. **Creates patients table** (if it doesn't exist)
2. **Identifies unique patient names** from existing health_records
3. **Creates patient entries** in the patients table for each unique name
4. **Adds patient_id column** to health_records
5. **Populates patient_id** values based on patient names
6. **Recreates the table** with the new schema including foreign key
7. **Copies all data** to the new table structure

**No data is lost** - all existing records are preserved with their patient relationships intact.

## Troubleshooting

### "Patient 'X' not found in database" Error

This shouldn't happen if migration ran successfully. If you see this:
1. Check that the patients table has entries: `sqlite3 data/health_bot.db "SELECT * FROM patients;"`
2. Verify migration completed: `python migrate_db.py --status`
3. If needed, restore from backup and re-run migration

### Database Locked Error

If you get a "database is locked" error:
- Stop the bot if it's running
- Make sure no other processes are accessing the database
- Retry the migration

### Restore from Backup

If something goes wrong:

```bash
# Find your backup file
ls -lh data/health_bot.db.backup_*

# Restore (replace TIMESTAMP with actual timestamp)
cp data/health_bot.db.backup_TIMESTAMP data/health_bot.db
```

## Migration Script Options

```bash
python migrate_db.py [OPTIONS]

Options:
  --db-path PATH    Path to database file (default: data/health_bot.db)
  --dry-run         Show what would be migrated without making changes
  --backup          Create backup before migration
  --force           Force migration even if already migrated (dangerous)
  --status          Only show migration status, don't migrate
```

## Example Workflow

```bash
# 1. Check status
python migrate_db.py --status

# 2. Dry run to see what will happen
python migrate_db.py --dry-run

# 3. Run migration with backup
python migrate_db.py --backup

# 4. Verify completion
python migrate_db.py --status

# 5. Start bot (migration won't run again)
python bot.py
```

## Production Deployment Checklist

- [ ] Stop the bot
- [ ] Check migration status: `python migrate_db.py --status`
- [ ] Create manual backup: `cp data/health_bot.db data/health_bot.db.backup_$(date +%Y%m%d_%H%M%S)`
- [ ] Run dry run: `python migrate_db.py --dry-run`
- [ ] Run migration: `python migrate_db.py --backup`
- [ ] Verify status: `python migrate_db.py --status`
- [ ] Test bot functionality
- [ ] Start bot: `python bot.py`

## Safety Features

✅ **Idempotent**: Safe to run multiple times  
✅ **Automatic backup**: Use `--backup` flag  
✅ **Dry run mode**: Test without making changes  
✅ **Status checking**: See what will happen before running  
✅ **No data loss**: All existing records are preserved  
✅ **Automatic**: Runs on bot startup if not already migrated  

## Need Help?

If you encounter issues:
1. Check the error message
2. Verify backup exists
3. Check migration status
4. Review database manually with: `sqlite3 data/health_bot.db`

