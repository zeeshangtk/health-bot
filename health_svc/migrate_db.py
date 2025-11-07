#!/usr/bin/env python3
"""
Database migration script for production use.
Safely migrates health_records table from patient TEXT to patient_id INTEGER foreign key.

Usage:
    python migrate_db.py [--db-path PATH] [--dry-run] [--backup]
    
Options:
    --db-path PATH    Path to database file (default: from config.py)
    --dry-run         Show what would be migrated without making changes
    --backup          Create backup before migration
    --force           Force migration even if already migrated (dangerous)
"""
import os
import sys
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import DATABASE_PATH
from storage.database import Database


def backup_database(db_path: str) -> str:
    """
    Create a backup of the database.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        Path to the backup file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    print(f"Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup created successfully")
    
    return backup_path


def check_migration_status(db_path: str) -> dict:
    """
    Check the current migration status of the database.
    
    Returns:
        dict with status information
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    # Check if health_records table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='health_records'
    """)
    table_exists = cursor.fetchone() is not None
    
    status = {
        "table_exists": table_exists,
        "needs_migration": False,
        "already_migrated": False,
        "patient_column_exists": False,
        "patient_id_column_exists": False,
        "record_count": 0,
        "unique_patients": []
    }
    
    if not table_exists:
        conn.close()
        return status
    
    # Check columns
    cursor.execute("PRAGMA table_info(health_records)")
    columns = {row[1]: row for row in cursor.fetchall()}
    
    status["patient_column_exists"] = "patient" in columns
    status["patient_id_column_exists"] = "patient_id" in columns
    
    if status["patient_id_column_exists"]:
        status["already_migrated"] = True
    elif status["patient_column_exists"]:
        status["needs_migration"] = True
        
        # Get record count and unique patients
        cursor.execute("SELECT COUNT(*) FROM health_records")
        status["record_count"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT DISTINCT patient FROM health_records")
        status["unique_patients"] = [row[0] for row in cursor.fetchall()]
    
    # Check patients table
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='patients'
    """)
    status["patients_table_exists"] = cursor.fetchone() is not None
    
    if status["patients_table_exists"]:
        cursor.execute("SELECT COUNT(*) FROM patients")
        status["patient_count"] = cursor.fetchone()[0]
    
    conn.close()
    return status


def print_status(status: dict) -> None:
    """Print migration status in a readable format."""
    print("\n" + "=" * 60)
    print("DATABASE MIGRATION STATUS")
    print("=" * 60)
    
    if not status["table_exists"]:
        print("⚠️  health_records table does not exist")
        print("   No migration needed - table will be created with new schema.")
        return
    
    print(f"health_records table exists: ✅")
    print(f"patient column exists: {'✅' if status['patient_column_exists'] else '❌'}")
    print(f"patient_id column exists: {'✅' if status['patient_id_column_exists'] else '❌'}")
    
    if status["patients_table_exists"]:
        print(f"patients table exists: ✅ ({status.get('patient_count', 0)} patients)")
    else:
        print(f"patients table exists: ❌")
    
    if status["already_migrated"]:
        print("\n✅ Database is already migrated!")
        print("   No action needed.")
    elif status["needs_migration"]:
        print("\n⚠️  Migration needed!")
        print(f"   Records to migrate: {status['record_count']}")
        print(f"   Unique patients: {len(status['unique_patients'])}")
        if status["unique_patients"]:
            print(f"   Patient names: {', '.join(status['unique_patients'][:5])}")
            if len(status["unique_patients"]) > 5:
                print(f"   ... and {len(status['unique_patients']) - 5} more")
    else:
        print("\n❓ Unknown state - table exists but has neither patient nor patient_id column")
        print("   This should not happen. Please check the database manually.")
    
    print("=" * 60 + "\n")


def run_migration(db_path: str, dry_run: bool = False, force: bool = False) -> bool:
    """
    Run the migration.
    
    Args:
        db_path: Path to database file
        dry_run: If True, don't make changes
        force: Force migration even if already migrated
        
    Returns:
        True if migration succeeded or was not needed
    """
    status = check_migration_status(db_path)
    print_status(status)
    
    if status["already_migrated"] and not force:
        print("✅ Migration not needed - database is already migrated.")
        return True
    
    if not status["needs_migration"] and not force:
        if not status["table_exists"]:
            print("ℹ️  No migration needed - table will be created automatically on first use.")
        else:
            print("⚠️  Migration not applicable - unknown table state.")
        return True
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print(f"\nWould migrate {status['record_count']} records")
        print(f"Would create/update {len(status['unique_patients'])} patients")
        return True
    
    print("🚀 Starting migration...")
    
    try:
        # Use Database class to run migration
        # This ensures we use the same migration logic as the application
        db = Database(db_path=db_path)
        
        # Verify migration completed
        verify_status = check_migration_status(db_path)
        if verify_status["already_migrated"]:
            print("✅ Migration completed successfully!")
            print(f"   Migrated {status['record_count']} records")
            print(f"   {verify_status.get('patient_count', 0)} patients in database")
            return True
        else:
            print("❌ Migration may have failed - database not in expected state")
            return False
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exception(*sys.exc_info())
        return False


def main():
    """Main entry point for migration script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate health_records table to use foreign key relationship"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=DATABASE_PATH,
        help=f"Path to database file (default: {DATABASE_PATH})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup before migration"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force migration even if already migrated (dangerous)"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Only show migration status, don't migrate"
    )
    
    args = parser.parse_args()
    
    db_path = args.db_path
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print(f"   If this is a new installation, the database will be created automatically.")
        sys.exit(1)
    
    print(f"Database path: {db_path}")
    print(f"File size: {os.path.getsize(db_path) / 1024:.2f} KB")
    
    if args.status:
        status = check_migration_status(db_path)
        print_status(status)
        sys.exit(0)
    
    # Create backup if requested
    if args.backup:
        backup_path = backup_database(db_path)
        print(f"💾 Backup saved to: {backup_path}\n")
    
    # Run migration
    success = run_migration(db_path, dry_run=args.dry_run, force=args.force)
    
    if success:
        print("\n✅ Migration process completed successfully")
        sys.exit(0)
    else:
        print("\n❌ Migration failed - check errors above")
        if args.backup:
            print(f"\n💡 A backup was created before migration: {backup_path}")
            print("   You can restore it if needed.")
        sys.exit(1)


if __name__ == "__main__":
    main()

