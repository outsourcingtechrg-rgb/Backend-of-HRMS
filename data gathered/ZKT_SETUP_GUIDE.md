# ZKT Attendance Sync - Quick Setup Guide

## Prerequisites

- Python 3.8+
- FastAPI application running
- MySQL database with HRMS schema
- Network connectivity to ZKT machine

## Installation Steps

### 1. Update `.env` File

```env
# Add these configurations
ZKT_MACHINE_IP=192.168.1.201
ZKT_MACHINE_PORT=4370
ZKT_SYNC_INTERVAL_MINUTES=10
```

### 2. Run Database Migration

```bash
# Generate migration (if needed)
alembic revision --autogenerate -m "Add synced_at to attendance"

# Or use the template
cp MIGRATION_TEMPLATE_SYNCED_AT.py alembic/versions/

# Apply migration
alembic upgrade head
```

### 3. Install Optional Dependencies (for real ZKT integration)

```bash
# For actual ZKT machine communication, install:
pip install pyzk
# or
pip install zkclibpy
```

### 4. Update Models (if not done)

The `Attendance` model has been updated with `synced_at` field in:

- `app/models/attendance.py`

### 5. Start Application

```bash
uvicorn app.main:app --reload
```

The sync scheduler will automatically start on application startup.

## File Structure

```
app/
├── background/
│   ├── __init__.py
│   ├── zkt_connector.py      # ZKT machine connector
│   └── sync_scheduler.py     # Background sync scheduler
├── models/
│   └── attendance.py         # Updated with synced_at
├── schemas/
│   ├── attendance.py         # Attendance schemas
│   └── employee.py           # Updated with EmployeeRead
├── crud/
│   └── attendance.py         # Attendance CRUD operations
└── api/v1/
    ├── attendance.py         # Attendance endpoints
    └── sync.py              # Sync management endpoints
```

## API Endpoints

### Attendance Management

- `GET /api/v1/attendance/` - List attendance
- `POST /api/v1/attendance/` - Create single attendance
- `POST /api/v1/attendance/bulk` - Bulk create attendance
- `GET /api/v1/attendance/{id}` - Get specific record
- `PUT /api/v1/attendance/{id}` - Update record
- `DELETE /api/v1/attendance/{id}` - Delete record

### Sync Management

- `GET /api/v1/sync/status` - Get current sync status
- `POST /api/v1/sync/trigger` - Manually trigger sync

### Employee Management (Enhanced)

- `GET /api/v1/employees/` - List employees with relationships
- `GET /api/v1/employees/{id}` - Get employee with relationships

## Testing Sync

### 1. Check Sync Status

```bash
curl http://localhost:8000/api/v1/sync/status
```

### 2. Trigger Manual Sync

```bash
curl -X POST http://localhost:8000/api/v1/sync/trigger
```

### 3. View Attendance Records

```bash
curl http://localhost:8000/api/v1/attendance/?limit=10
```

### 4. Test Employee Read with Relations

```bash
curl http://localhost:8000/api/v1/employees/1
```

## Configuration

### Sync Interval

In `app/background/sync_scheduler.py`:

```python
scheduler = AttendanceSyncScheduler(sync_interval_minutes=10)
```

### ZKT Machine Details

In `.env`:

```env
ZKT_MACHINE_IP=192.168.1.201
ZKT_MACHINE_PORT=4370
```

## Implementing Real ZKT Integration

The current implementation provides a template for ZKT integration. To connect to actual ZKT machines:

### Option 1: Using PyZK

```python
# In app/background/zkt_connector.py
from pyzk import ZK

def _fetch_from_device(self, since=None):
    zk = ZK(self.machine_ip, port=self.machine_port, timeout=self.timeout)
    try:
        zk.connect()
        attendances = zk.get_attendance()
        return self._convert_attendances(attendances, since)
    finally:
        zk.disconnect()
```

### Option 2: Using ZKClibPy

```python
# Similar implementation with zkclibpy library
```

### Step-by-Step Integration:

1. Install the appropriate ZKT library
2. Update `_fetch_from_device()` in `app/background/zkt_connector.py`
3. Implement `_convert_attendances()` to map ZKT data to our schema
4. Test with `POST /api/v1/sync/trigger`

## Troubleshooting

### Sync Not Running

1. Check application logs for startup errors
2. Verify `.env` file is correctly formatted
3. Ensure database connection is working
4. Check `GET /api/v1/sync/status` endpoint

### Connection Issues

1. Verify ZKT machine IP: `ping <ZKT_MACHINE_IP>`
2. Check port: `telnet <ZKT_MACHINE_IP> 4370`
3. Verify firewall rules allow connection
4. Check ZKT machine logs

### No Records Being Synced

1. Verify ZKT machine has attendance data
2. Check `synced_at` values in database
3. Manually trigger sync and check logs
4. Review `_fetch_from_device()` implementation

## Monitoring

### Logs to Watch

```
Starting ZKT attendance sync scheduler...
Successfully connected to ZKT machine...
Fetched N attendance records from ZKT machine
Successfully synced N attendance records
```

### Database Queries

```sql
-- Check last sync time
SELECT MAX(synced_at) as last_sync FROM attendance;

-- Check sync frequency
SELECT synced_at, COUNT(*) as count
FROM attendance
GROUP BY DATE(synced_at)
ORDER BY synced_at DESC;

-- Find unsynced records
SELECT COUNT(*) FROM attendance WHERE synced_at IS NULL;
```

## Support & References

- Attendance Model: `app/models/attendance.py`
- Sync Documentation: `ZKT_SYNC_DOCUMENTATION.md`
- ZKT Connector: `app/background/zkt_connector.py`
- Sync Scheduler: `app/background/sync_scheduler.py`

## Next Steps

1. ✅ Update `.env` with ZKT machine details
2. ✅ Run database migration for `synced_at` field
3. ✅ Implement real ZKT connector library integration
4. ✅ Test sync with `POST /api/v1/sync/trigger`
5. ✅ Monitor logs and verify records are syncing
6. ✅ Set up alerting for sync failures (optional)
