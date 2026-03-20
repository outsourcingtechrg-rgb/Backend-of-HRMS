# Attendance Sync Scheduler Configuration Guide

## Overview

The attendance sync system automatically synchronizes attendance data from ZKT devices to the HRMS database. It can be configured to run on a custom schedule with adjustable intervals.

## Architecture

### Components

1. **AttendanceSync Model** (`app/models/attendanceSync.py`)
   - Stores sync configuration and status
   - Fields:
     - `device_ip`: IP address of ZKT device
     - `sync_interval_minutes`: How often to sync (in minutes)
     - `last_synced_at`: Last successful sync timestamp
     - `is_enabled`: Enable/disable sync
     - `created_at`: When record was created
     - `updated_at`: Last configuration update

2. **Sync Service** (`app/background/attendance_sync_service.py`)
   - Handles data fetching and database insertion
   - Creates placeholder employees for missing users
   - Logs all operations for debugging
   - Automatically creates FK references (Department, Role, Shift)

3. **ZKT Connection** (`app/background/zkteco.py`)
   - Communicates directly with ZKT device
   - Fetches attendance records since last sync
   - Comprehensive error handling and logging

## API Endpoints

### 1. Get Sync Status

```
GET /api/v1/attendance-sync/status
```

Returns current sync configuration and last sync time.

**Response:**

```json
{
  "id": 1,
  "device_ip": "172.16.32.184",
  "sync_interval_minutes": 10,
  "is_enabled": true,
  "last_synced_at": "2026-03-14T10:30:45.123456",
  "created_at": "2026-03-14T09:00:00.000000",
  "updated_at": "2026-03-14T10:00:00.000000"
}
```

### 2. Update Sync Settings

```
PATCH /api/v1/attendance-sync/settings
Content-Type: application/json

{
  "sync_interval_minutes": 5,
  "is_enabled": true
}
```

**Parameters:**

- `sync_interval_minutes`: (optional) Sync interval in minutes (minimum: 1)
- `is_enabled`: (optional) Enable/disable sync

### 3. Manual Sync Trigger

```
POST /api/v1/attendance-sync/run
```

Immediately trigger a sync operation (doesn't wait for schedule).

**Response:**

```json
{
  "success": true,
  "message": "Sync completed",
  "data": {
    "inserted": 45,
    "records_received": 50,
    "skipped": 5,
    "missing_employees": 5,
    "last_synced_at": "2026-03-14T10:35:22.654321"
  }
}
```

### 4. Reset Sync Time (Initial Data Load)

```
POST /api/v1/attendance-sync/reset-sync-time
```

Reset last sync to 2020-01-01 to fetch ALL historical attendance data from device.

**Warning:** This will attempt to sync all records since 2020, which may take time and create many database records.

**Response:**

```json
{
  "success": true,
  "message": "Sync time reset to 2020-01-01",
  "last_synced_at": "2020-01-01T00:00:00"
}
```

After reset:

1. Configure sync settings: `PATCH /api/v1/attendance-sync/settings` (optional)
2. Trigger manual sync: `POST /api/v1/attendance-sync/run`
3. Monitor progress via logs

## Configuration Examples

### Example 1: Initial Setup (Load All Data)

```bash
# 1. Reset sync time to get all historical data
curl -X POST http://localhost:8000/api/v1/attendance-sync/reset-sync-time

# 2. Set sync interval to 15 minutes
curl -X PATCH http://localhost:8000/api/v1/attendance-sync/settings \
  -H "Content-Type: application/json" \
  -d '{"sync_interval_minutes": 15}'

# 3. Trigger manual sync
curl -X POST http://localhost:8000/api/v1/attendance-sync/run
```

### Example 2: Frequent Sync (Every 5 Minutes)

```bash
curl -X PATCH http://localhost:8000/api/v1/attendance-sync/settings \
  -H "Content-Type: application/json" \
  -d '{"sync_interval_minutes": 5}'
```

### Example 3: Disable Sync Temporarily

```bash
curl -X PATCH http://localhost:8000/api/v1/attendance-sync/settings \
  -H "Content-Type: application/json" \
  -d '{"is_enabled": false}'
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

## Workflow: Initial Data Load

### Scenario: Get all attendance from device since day one

```
1. Connect to device
2. Reset sync time to 2020-01-01 via API
   POST /api/v1/attendance-sync/reset-sync-time

3. Check current settings
   GET /api/v1/attendance-sync/status

4. Manually trigger sync
   POST /api/v1/attendance-sync/run

5. Monitor logs for progress:
   - Inserted X records
   - Skipped Y records
   - Created Z placeholder employees

6. Configure auto-sync schedule
   PATCH /api/v1/attendance-sync/settings
   {"sync_interval_minutes": 10}
```

## Logging

The system logs all sync operations. Check logs for:

- Connection attempts
- Records fetched
- Errors encountered
- Placeholder creation
- Database insertion failures

**Log locations:**

- Application logs: stdout/stderr from uvicorn
- Database logs: MySQL error log

**Common log entries:**

```
INFO - Starting attendance sync...
INFO - Last sync: 2026-03-14 10:30:00
INFO - Fetched 50 records from device
INFO - Creating placeholder employee for ID 123
INFO - Sync completed: 45 inserted, 50 total, 5 skipped, 5 missing employees
```

## Troubleshooting

### Issue: "No records synced"

- Check device IP in settings
- Verify device is reachable: `ping 172.16.32.184`
- Verify attendance records exist on device
- Check last_synced_at timestamp

### Issue: "Connection timeout"

- Ensure ZKT device is powered on
- Check network connectivity
- Verify firewall allows port 4370

### Issue: "Permission denied / Foreign key constraint"

- New placeholders created without proper default department/role/shift
- System should auto-create defaults, check logs for errors

### Issue: "Duplicate entry" errors

- Attendance records already synced
- This is normal and handled gracefully
- Unique constraint prevents duplicates

## Performance Considerations

- **Default interval:** 10 minutes (adjustable)
- **Minimum interval:** 1 minute
- **Recommended interval:** 10-15 minutes for production
- **Database size:** Monitor as attendance records accumulate

## Initial Setup Steps

1. **Initialize Database:**

   ```bash
   alembic upgrade head
   ```

2. **Verify Settings:**

   ```bash
   curl http://localhost:8000/api/v1/attendance-sync/status
   ```

3. **Reset to Load All Data:**

   ```bash
   curl -X POST http://localhost:8000/api/v1/attendance-sync/reset-sync-time
   ```

4. **Trigger Manual Sync:**

   ```bash
   curl -X POST http://localhost:8000/api/v1/attendance-sync/run
   ```

5. **Check Status:**

   ```bash
   curl http://localhost:8000/api/v1/attendance-sync/status
   ```

6. **Configure Schedule:**
   ```bash
   curl -X PATCH http://localhost:8000/api/v1/attendance-sync/settings \
     -H "Content-Type: application/json" \
     -d '{"sync_interval_minutes": 10}'
   ```

## Next Steps

- Integrate with frontend UI to display sync status
- Add email alerts for sync failures
- Create dashboard for attendance statistics
- Implement data validation rules
- Add employee mapping interface to link placeholder employees to real employees
