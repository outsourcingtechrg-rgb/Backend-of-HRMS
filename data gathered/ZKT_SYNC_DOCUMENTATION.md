# ZKT Attendance Sync System Documentation

## Overview

This document describes the automated attendance synchronization system that fetches attendance data from ZKT machines every 10 minutes and stores it in the HRMS database.

## Components

### 1. **Employee Schema (EmployeeRead)**

- **Location**: `app/schemas/employee.py`
- **Purpose**: Enhanced employee read schema with nested relationships
- **Features**:
  - Includes related Role, Department, and Shift objects
  - Used for GET endpoints to provide complete employee information

### 2. **Attendance Model**

- **Location**: `app/models/attendance.py`
- **New Field**: `synced_at` - Timestamp tracking when record was synced from ZKT
- **Purpose**: Track attendance records with sync timestamps

### 3. **Attendance Schemas**

- **Location**: `app/schemas/attendance.py`
- **Schemas**:
  - `AttendanceCreate`: For creating individual records
  - `AttendanceUpdate`: For updating records
  - `AttendanceBulkCreate`: For bulk import from ZKT
  - `AttendanceSyncStatus`: For sync status reporting

### 4. **Attendance CRUD Operations**

- **Location**: `app/crud/attendance.py`
- **Key Functions**:
  - `create_attendance()`: Create single record
  - `create_bulk_attendance()`: Bulk create with synced_at timestamp
  - `get_last_synced_time()`: Get timestamp of last sync
  - `get_attendance_since()`: Fetch records since specific time

### 5. **Attendance API Endpoints**

- **Location**: `app/api/v1/attendance.py`
- **Endpoints**:
  ```
  POST   /api/v1/attendance/              - Create single attendance
  POST   /api/v1/attendance/bulk         - Bulk create attendance
  GET    /api/v1/attendance/             - List attendance (with filters)
  GET    /api/v1/attendance/{id}         - Get single record
  GET    /api/v1/attendance/employee/{employee_id}/
  GET    /api/v1/attendance/employee/{employee_id}/date/{date}
  PUT    /api/v1/attendance/{id}         - Update record
  DELETE /api/v1/attendance/{id}         - Delete record
  GET    /api/v1/attendance/sync/status  - Get sync status
  ```

### 6. **ZKT Connector**

- **Location**: `app/background/zkt_connector.py`
- **Class**: `ZKTConnector`
- **Features**:
  - Connects to ZKT machine via IP:Port
  - Fetches attendance records
  - Handles connection errors gracefully
  - Configurable timeout

### 7. **Sync Scheduler**

- **Location**: `app/background/sync_scheduler.py`
- **Class**: `AttendanceSyncScheduler`
- **Features**:
  - Runs synchronization every 10 minutes (configurable)
  - Uses `synced_at` timestamp to fetch only new records
  - Bulk inserts records for performance
  - Tracks sync status and metrics
  - Supports manual sync trigger

### 8. **Sync Management API**

- **Location**: `app/api/v1/sync.py`
- **Endpoints**:
  ```
  GET  /api/v1/sync/status   - Get sync status
  POST /api/v1/sync/trigger  - Manually trigger sync
  ```

## Configuration

### Environment Variables

Add to `.env`:

```
# ZKT Machine Configuration
ZKT_MACHINE_IP=192.168.1.201      # IP address of ZKT machine
ZKT_MACHINE_PORT=4370              # Port (default: 4370)
ZKT_SYNC_INTERVAL_MINUTES=10       # Sync interval (default: 10)
```

### Database Migration

Add this field to your Attendance table via Alembic:

```python
# In migration file
synced_at = sa.Column(sa.DateTime(), nullable=True)
```

## How It Works

### 1. **Application Startup**

- FastAPI startup event triggers `start_sync_scheduler()`
- Scheduler initializes `AttendanceSyncScheduler` instance
- Background async task begins running

### 2. **Sync Cycle (Every 10 Minutes)**

```
1. Query last synced timestamp from database
2. Connect to ZKT machine
3. Fetch attendance records since last sync
4. Convert to AttendanceCreate schema
5. Bulk insert into database with current synced_at
6. Update sync status and metrics
7. Disconnect from ZKT machine
```

### 3. **Timestamp-Based Tracking**

- `synced_at` field marks when record was pulled from ZKT
- On next sync, query `get_last_synced_time()` to find last sync point
- Fetch only records newer than this timestamp from ZKT
- Prevents duplicate syncing

### 4. **Error Handling**

- Connection failures don't crash the scheduler
- Errors logged for monitoring
- Scheduler continues running despite transient failures
- Status available via `/api/v1/sync/status` endpoint

## API Usage Examples

### List All Attendance

```bash
curl http://localhost:8000/api/v1/attendance/
```

### Get Attendance for Specific Employee

```bash
curl http://localhost:8000/api/v1/attendance/employee/123/?limit=50
```

### Get Today's Attendance for Employee

```bash
curl "http://localhost:8000/api/v1/attendance/employee/123/date/2026-03-07"
```

### Get Sync Status

```bash
curl http://localhost:8000/api/v1/sync/status
```

Response:

```json
{
  "is_running": true,
  "last_sync_time": "2026-03-07T12:30:45.123456",
  "next_sync_time": "2026-03-07T12:40:45.123456",
  "total_synced": 2150,
  "last_error": null,
  "sync_count": 45
}
```

### Manually Trigger Sync

```bash
curl -X POST http://localhost:8000/api/v1/sync/trigger
```

### Create Bulk Attendance (from ZKT)

```bash
curl -X POST http://localhost:8000/api/v1/attendance/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "records": [
      {
        "employee_id": 1,
        "employee_name": "John Doe",
        "attendance_date": "2026-03-07",
        "attendance_time": "09:30:00",
        "punch": true,
        "attendance_mode": "onsite"
      }
    ]
  }'
```

## Employee API with Relationships

### Get Employee List (with relations)

```bash
curl http://localhost:8000/api/v1/employees/
```

Response includes nested role, department, and shift:

```json
{
  "id": 1,
  "employee_id": "EMP001",
  "f_name": "John",
  "l_name": "Doe",
  "email": "john@example.com",
  "role": {
    "id": 1,
    "name": "HR Manager",
    "level": 3
  },
  "department": {
    "id": 1,
    "department": "Human Resources"
  },
  "shift": {
    "id": 1,
    "name": "Morning",
    "shift_start_timing": "09:00:00",
    "shift_end_timing": "17:00:00"
  },
  "employment_status": "active",
  "created_at": "2026-03-01T10:00:00"
}
```

## Database Schema

```sql
ALTER TABLE attendance ADD COLUMN synced_at DATETIME NULL;
CREATE INDEX idx_attendance_synced_at ON attendance(synced_at);
```

## Monitoring & Troubleshooting

### Check Sync Status

- Visit `/api/v1/sync/status` to see:
  - When last sync occurred
  - When next sync is scheduled
  - Total records synced
  - Any errors

### Monitor Logs

- Filter application logs for `AttendanceSyncScheduler`
- Look for `ZKT Connector` messages for connection issues

### Manual Sync Trigger

- Use `/api/v1/sync/trigger` to force immediate sync
- Useful for testing or recovering from missed syncs

### Common Issues

**Issue**: Connection timeout to ZKT machine

- Check IP address in `.env` is correct
- Verify ZKT machine is powered on and network accessible
- Check firewall rules for port 4370

**Issue**: No new records being synced

- Verify ZKT machine has new attendance records
- Check `synced_at` timestamps in database
- Manually trigger sync and check logs

**Issue**: Duplicate records

- `synced_at` prevents duplicates from same machine
- If records are from different source, add source tracking to `extra_data`

## Future Enhancements

1. **Multi-Machine Support**: Connect to multiple ZKT machines
2. **Real-time Sync**: Use ZKT event notifications instead of polling
3. **Data Validation**: Additional checks for employee existence, date ranges
4. **Retry Logic**: Exponential backoff for failed syncs
5. **Batch Processing**: Configurable batch sizes for large datasets
6. **Audit Trail**: Track sync source, user, and modifications
7. **Alerting**: Notifications for sync failures or delays

## Implementation Notes

- Sync runs asynchronously in background, doesn't block API requests
- Database transactions are committed per bulk insert for data consistency
- Timestamps use UTC for consistency across timezones
- Attendance records are immutable after sync (updates reflect corrections, not overwrites)
- Consider adding indexes on `employee_id`, `attendance_date`, and `synced_at` for performance
