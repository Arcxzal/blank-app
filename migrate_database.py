#!/usr/bin/env python3
"""
Database Migration Script
Adds patient_id column to existing pressure_samples table
"""

import sqlite3
import os
from pathlib import Path

# Database path
DB_PATH = Path("/workspaces/blank-app/backend/sensor_data.db")

def migrate_database():
    """Add patient_id column to pressure_samples table"""
    
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        print("   Creating new database with correct schema...")
        # Database will be created by init_demo_patient.py
        return False
    
    print(f"🔄 Migrating database at {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if patient_id column already exists
        cursor.execute("PRAGMA table_info(pressure_samples)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'patient_id' in columns:
            print("✅ patient_id column already exists - no migration needed")
            conn.close()
            return True
        
        # Add patient_id column
        print("   Adding patient_id column to pressure_samples...")
        cursor.execute("""
            ALTER TABLE pressure_samples 
            ADD COLUMN patient_id INTEGER
        """)
        
        # Set all existing records to NULL (will be handled by backend)
        cursor.execute("""
            UPDATE pressure_samples 
            SET patient_id = NULL
        """)
        
        conn.commit()
        print("✅ Migration successful!")
        print("   Note: Existing data has patient_id=NULL (backward compatible)")
        
    except sqlite3.OperationalError as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
    
    return True


def recreate_database():
    """Backup old database and create new one"""
    
    if DB_PATH.exists():
        backup_path = DB_PATH.with_suffix('.db.backup')
        print(f"📦 Backing up existing database to {backup_path}")
        import shutil
        shutil.copy(DB_PATH, backup_path)
        
        print(f"🗑️  Removing old database...")
        DB_PATH.unlink()
    
    print("✨ Database will be recreated with new schema on next backend start")
    print("   Run: python3 init_demo_patient.py")


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("Database Migration Tool")
    print("=" * 60)
    print()
    
    if "--recreate" in sys.argv:
        print("⚠️  RECREATE MODE: This will delete all existing data!")
        print()
        response = input("Are you sure? Type 'yes' to continue: ")
        if response.lower() == 'yes':
            recreate_database()
        else:
            print("❌ Cancelled")
            sys.exit(1)
    else:
        # Try migration first
        success = migrate_database()
        
        if not success and DB_PATH.exists():
            print()
            print("⚠️  Migration failed. Options:")
            print("   1. Run with --recreate flag to delete and recreate database")
            print("      Warning: This will delete all existing data!")
            print()
            print("   Command: python3 migrate_database.py --recreate")
            sys.exit(1)
        elif not DB_PATH.exists():
            print()
            print("✨ No database found. Run this to create it:")
            print("   python3 init_demo_patient.py")
