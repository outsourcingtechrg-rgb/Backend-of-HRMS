#!/usr/bin/env python3
"""
Initial Setup Script for Attendance Sync System
This script initializes the database with proper default values for the scheduler
"""

import sys
from datetime import datetime
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, '.')

from app.core.database import SessionLocal
from app.models.attendanceSync import AttendanceSync
from app.models.department import Department
from app.models.role import Role
from app.models.shift import Shift
from datetime import time


def init_sync_settings():
    """Initialize or update sync settings in database"""
    db = SessionLocal()
    try:
        DEVICE_IP = "172.16.32.184"
        
        # Check if sync settings already exist
        sync_config = db.query(AttendanceSync).filter(
            AttendanceSync.device_ip == DEVICE_IP
        ).first()
        
        if sync_config:
            print(f"✓ Sync settings already exist for {DEVICE_IP}")
            print(f"  - Sync interval: {sync_config.sync_interval_minutes} minutes")
            print(f"  - Enabled: {sync_config.is_enabled}")
            print(f"  - Last synced: {sync_config.last_synced_at}")
        else:
            print(f"Creating sync settings for {DEVICE_IP}...")
            sync_config = AttendanceSync(
                device_ip=DEVICE_IP,
                sync_interval_minutes=10,                    # Sync every 10 minutes
                is_enabled=True,                             # Enabled by default
                last_synced_at=datetime(2020, 1, 1),        # Start from 2020
            )
            db.add(sync_config)
            db.commit()
            print(f"✓ Sync settings created successfully")
            print(f"  - Device IP: {sync_config.device_ip}")
            print(f"  - Sync interval: {sync_config.sync_interval_minutes} minutes")
            print(f"  - Enabled: {sync_config.is_enabled}")
            print(f"  - Last synced: {sync_config.last_synced_at}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error initializing sync settings: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def init_defaults():
    """Initialize default Department, Role, and Shift"""
    db = SessionLocal()
    try:
        # Check or create default Department
        dept = db.query(Department).filter(
            Department.name == "Placeholder Department"
        ).first()
        
        if not dept:
            print("Creating default Department...")
            dept = Department(name="Placeholder Department")
            db.add(dept)
            db.flush()
            print(f"✓ Default Department created (ID: {dept.id})")
        else:
            print(f"✓ Default Department already exists (ID: {dept.id})")
        
        # Check or create default Role
        role = db.query(Role).filter(Role.level == 1).first()
        
        if not role:
            print("Creating default Role...")
            role = Role(level=1, name="Staff")
            db.add(role)
            db.flush()
            print(f"✓ Default Role created (ID: {role.id})")
        else:
            print(f"✓ Default Role already exists (ID: {role.id})")
        
        # Check or create default Shift
        shift = db.query(Shift).filter(
            Shift.shift_start_timing == time(9, 0, 0),
            Shift.shift_end_timing == time(17, 0, 0)
        ).first()
        
        if not shift:
            print("Creating default Shift...")
            shift = Shift(
                name="Default Shift",
                shift_start_timing=time(9, 0, 0),
                shift_end_timing=time(17, 0, 0),
                saturday_on=False,
                allow_remote=False
            )
            db.add(shift)
            db.flush()
            print(f"✓ Default Shift created (ID: {shift.id})")
        else:
            print(f"✓ Default Shift already exists (ID: {shift.id})")
        
        db.commit()
        return True
        
    except Exception as e:
        print(f"✗ Error initializing defaults: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def check_tables():
    """Check if required tables exist"""
    db = SessionLocal()
    try:
        # Try to query each table
        tables_ok = True
        
        try:
            count = db.query(AttendanceSync).count()
            print(f"✓ attendance_sync table exists ({count} records)")
        except Exception as e:
            print(f"✗ attendance_sync table error: {e}")
            tables_ok = False
        
        try:
            count = db.query(Department).count()
            print(f"✓ departments table exists ({count} records)")
        except Exception as e:
            print(f"✗ departments table error: {e}")
            tables_ok = False
        
        try:
            count = db.query(Role).count()
            print(f"✓ roles table exists ({count} records)")
        except Exception as e:
            print(f"✗ roles table error: {e}")
            tables_ok = False
        
        try:
            count = db.query(Shift).count()
            print(f"✓ shifts table exists ({count} records)")
        except Exception as e:
            print(f"✗ shifts table error: {e}")
            tables_ok = False
        
        return tables_ok
        
    except Exception as e:
        print(f"✗ Database connection error: {e}")
        return False
    finally:
        db.close()


def main():
    print("=" * 60)
    print("Attendance Sync System - Initialization Script")
    print("=" * 60)
    print()
    
    print("Step 1: Checking database tables...")
    print("-" * 60)
    if not check_tables():
        print("✗ Some tables are missing. Please run: alembic upgrade head")
        return False
    print()
    
    print("Step 2: Initializing default values...")
    print("-" * 60)
    if not init_defaults():
        print("✗ Failed to initialize defaults")
        return False
    print()
    
    print("Step 3: Initializing sync settings...")
    print("-" * 60)
    if not init_sync_settings():
        print("✗ Failed to initialize sync settings")
        return False
    print()
    
    print("=" * 60)
    print("✓ Initialization completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Start your FastAPI application: uvicorn app.main:app --reload")
    print("2. Access sync settings: GET http://localhost:8000/api/v1/attendance-sync/status")
    print("3. Trigger sync: POST http://localhost:8000/api/v1/attendance-sync/run")
    print("4. Load all historical data: POST http://localhost:8000/api/v1/attendance-sync/reset-sync-time")
    print()
    print("For more info, see: SCHEDULER_CONFIGURATION_GUIDE.md")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
