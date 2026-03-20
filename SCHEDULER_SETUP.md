# Attendance Sync System - Setup & Configuration

## Overview

The Attendance Sync System automatically synchronizes attendance data from ZKT biometric devices to the HRMS database. It includes:

- **Configurable sync intervals** (stored in database)
- **Automatic placeholder employee creation** (for missing employees)
- **Scheduled background synchronization** (10-minute default)
- **Manual sync triggers** via API
- **Comprehensive logging** for debugging
- **Error recovery** with graceful degradation

## Files Changed/Created

### 1. Updated Models

- **`app/models/attendanceSync.py`**
  - Added `sync_interval_minutes` (configurable)
  - Added `is_enabled` (control sync)
  - Removed `synced_time` (unused)
  - Added `created_at`, `updated_at` timestamps

### 2. Updated Services

- **`app/background/attendance_sync_service.py`**
  - Creates placeholders for missing employees
  - Creates default Department, Role, Shift
  - Comprehensive error handling and logging
  - Returns detailed sync statistics

- **`app/background/zkteco.py`**
  - Enhanced logging at each step
  - Better error categorization
  - Proper connection handling

- **`app/background/sync_scheduler.py`**
  - Reads sync interval from database dynamically
  - Checks `is_enabled` flag each cycle
  - Updates interval if changed in database
  - Auto-creates sync settings if missing

### 3. API Improvements

- **`app/api/v1/attendance_sync.py`**
  - `GET /api/v1/attendance-sync/status` - Get current settings
  - `PATCH /api/v1/attendance-sync/settings` - Update settings
  - `POST /api/v1/attendance-sync/run` - Manual sync
  - `POST /api/v1/attendance-sync/reset-sync-time` - Load all historical data

### 4. New Files

- **`app/schemas/sync_settings.py`** - Request/response schemas for sync API
- **`init_sync_system.py`** - Setup script
- **`alembic/versions/update_attendance_sync_schema.py`** - Database migration
- **`SCHEDULER_CONFIGURATION_GUIDE.md`** - Complete configuration guide

## Installation & Setup

### Step 1: Run Database Migration

```bash
cd c:\Users\ehsan javed\Desktop\ehsan\HRMS\backend
alembic upgrade head
```

This updates the `attendance_sync` table schema with new fields.

### Step 2: Initialize System

```bash
python init_sync_system.py
```

This script:

- ✓ Verifies database tables exist
- ✓ Creates default Department, Role, Shift
- ✓ Creates sync settings record
- ✓ Sets initial last_synced_at to 2020-01-01 (to get all historical data)

### Step 3: Start API Server

```bash
uvicorn app.main:app --reload
```

The sync scheduler will:

- Automatically start on app startup
- Begin syncing every 10 minutes
- Create placeholder employees as needed

### Step 4: Verify Setup

```bash
curl http://localhost:8000/api/v1/attendance-sync/status
```

Expected response:

```json
{
  "id": 1,
  "device_ip": "172.16.32.184",
  "sync_interval_minutes": 10,
  "is_enabled": true,
  "last_synced_at": "2020-01-01T00:00:00",
  "created_at": "2026-03-14T14:00:00",
  "updated_at": "2026-03-14T14:00:00"
}
```

## Configuration Options

### Change Sync Interval

```bash
# Sync every 5 minutes
curl -X PATCH http://localhost:8000/api/v1/attendance-sync/settings \
  -H "Content-Type: application/json" \
  -d '{"sync_interval_minutes": 5}'
```

### Disable Sync

```bash
curl -X PATCH http://localhost:8000/api/v1/attendance-sync/settings \
  -H "Content-Type: application/json" \
  -d '{"is_enabled": false}'
```

### Enable Sync

```bash
curl -X PATCH http://localhost:8000/api/v1/attendance-sync/settings \
  -H "Content-Type: application/json" \
  -d '{"is_enabled": true}'
```

### Trigger Manual Sync

```bash
curl -X POST http://localhost:8000/api/v1/attendance-sync/run
```

### Load All Historical Data

```bash
# Reset sync to beginning of time (2020-01-01)
curl -X POST http://localhost:8000/api/v1/attendance-sync/reset-sync-time

# Then trigger manual sync to start import
curl -X POST http://localhost:8000/api/v1/attendance-sync/run
```

## Data Flow

```
1. Sync Scheduler (every N minutes)
   ↓
2. Read settings from AttendanceSync table
   - Get sync_interval_minutes
   - Check is_enabled flag
   ↓
3. Fetch Attendance from ZKT Device
   - Query device using last_synced_at timestamp
   ↓
4. Get or Create Defaults
   - Department: "Placeholder Department"
   - Role: Level 1 "Staff"
   - Shift: 09:00-17:00 (8 hours)
   ↓
5. Process Records
   - Identify missing employees
   - Create placeholder employees for missing IDs
   - Convert records to Attendance objects
   ↓
6. Insert into Database
   - Bulk insert attendance records
   - Update last_synced_at timestamp
   ↓
7. Log Results
   - Records inserted
   - Placeholders created
   - Errors encountered
```

## Database Schema

### AttendanceSync Table

```sql
CREATE TABLE attendance_sync (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_ip VARCHAR(255) UNIQUE NOT NULL,
    last_synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sync_interval_minutes INT NOT NULL DEFAULT 10,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## Troubleshooting

### Sync Not Starting

1. Check if application started: `ps aux | grep uvicorn`
2. Verify database connection: `python init_sync_system.py`
3. Check application logs for errors
4. Verify device is reachable: `ping 172.16.32.184`

### No Records Synced

1. Check device has attendance records
2. Verify last_synced_at is set correctly
3. Reset sync time: `POST /api/v1/attendance-sync/reset-sync-time`
4. Check logs for device connection errors

### Duplicate Employees

- The database has a UNIQUE constraint on (employee_id, attendance_date, attendance_time)
- Duplicates are automatically skipped
- Never an issue with the unique constraint in place

### Configuration Reset

```bash
# Get current status
GET /api/v1/attendance-sync/status

# Update any field needed
PATCH /api/v1/attendance-sync/settings
{
    "sync_interval_minutes": 10,
    "is_enabled": true
}
```

## Monitoring

### Check Latest Sync Status

```bash
curl http://localhost:8000/api/v1/attendance-sync/status
```

### View Application Logs

Check uvicorn console output for:

- INFO: Starting scheduled attendance sync...
- INFO: Fetched X records from device
- WARNING: Creating Y placeholder employees
- INFO: Successfully synced Z attendance records
- ERROR: Connection timeout (if device unreachable)

### Database Queries

```sql
-- Check last sync time
SELECT device_ip, last_synced_at, sync_interval_minutes, is_enabled
FROM attendance_sync;

-- Count attendance records
SELECT COUNT(*) FROM attendance;

-- Count placeholder employees
SELECT COUNT(*) FROM employees
WHERE email LIKE 'emp_%@hrms.internal';

-- View recent sync activity
SELECT * FROM attendance
WHERE synced_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
ORDER BY synced_at DESC;
```

## Common Tasks

### Change Device IP

Currently hardcoded to `172.16.32.184`. To change:

1. Edit `app/background/zkteco.py`, line: `DEVICE_IP = "172.16.32.184"`
2. Edit `app/background/attendance_sync_service.py`, line: `DEVICE_IP = "172.16.32.184"`
3. Optionally support multiple devices in future

### Add Custom Validation

Edit `app/background/attendance_sync_service.py` in the sync loop to add:

- Punch time validation
- Duplicate detection
- Business rule checks

### Export Attendance Data

Use standard FastAPI endpoints to export:

- `/api/v1/attendance/` - List all attendance
- `/api/v1/employees/` - List employees with attendance relationships

## Performance Notes

- **Default interval:** 10 minutes
- **Minimum interval:** 1 minute (not recommended for production)
- **Recommended interval:** 10-15 minutes
- **Database impact:** Low, uses efficient bulk inserts
- **Network impact:** Low, only fetches records since last sync

## Security Considerations

- Device IP hardcoded (could be moved to environment variables)
- No authentication to ZKT device (most are on secure internal networks)
- Database credentials in environment/config
- API endpoints should be protected with auth middleware

## Next Steps

1. ✓ Run `alembic upgrade head`
2. ✓ Run `python init_sync_system.py`
3. ✓ Start API: `uvicorn app.main:app --reload`
4. ✓ Verify status: `GET /api/v1/attendance-sync/status`
5. ✓ Load data: `POST /api/v1/attendance-sync/reset-sync-time`
6. ✓ Trigger sync: `POST /api/v1/attendance-sync/run`
7. ✓ Monitor progress via logs

## Support

For detailed configuration options, see: `SCHEDULER_CONFIGURATION_GUIDE.md`

For API endpoint details, see: `app/api/v1/attendance_sync.py`

For data model details, see: `app/models/attendanceSync.py`
