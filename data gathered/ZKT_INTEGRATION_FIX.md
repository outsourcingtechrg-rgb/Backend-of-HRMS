# ZKT Attendance Machine - Integration Fix Guide

## Problem Identified

The ZKT attendance machine connector was not fetching data from the device. The issue was that `app/background/zkt_connector.py` had placeholder code that:

- Used raw socket connections instead of the proper `pyzk` library
- The `_fetch_from_device()` method returned an empty list
- Was not actually communicating with the ZK device

## Solution Implemented

### 1. **Updated ZKT Connector** (`app/background/zkt_connector.py`)

- Now uses the **pyzk library** (already installed: v0.9)
- Properly connects to ZK device using `ZK()` class
- Fetches users to create employee ID → Name mapping
- Fetches all attendance records with proper error handling
- Returns data in the correct format expected by the system:
  ```python
  {
      'employee_id': int,
      'employee_name': str,
      'attendance_date': date,
      'attendance_time': time,  # ← Time component only (not datetime)
      'punch': bool,  # ← True for IN, False for OUT
      'attendance_mode': 'onsite'
  }
  ```

### 2. **Key Features**

- ✅ Uses pyzk library for actual device communication
- ✅ Disables device during fetch to prevent conflicts
- ✅ Properly maps punch types (0=IN/True, 1=OUT/False)
- ✅ Filters records by date if `since` parameter provided
- ✅ Comprehensive error handling and logging
- ✅ Automatically re-enables device after fetch
- ✅ Handles disconnection properly

## Testing the Fix

### Option 1: Run Connection Test

```bash
cd testRun
python main.py
```

This will:

- ✅ Test connection to the device at IP 172.16.32.184:4370
- ✅ Fetch and display all attendance records
- ✅ Show employee ID, name, date, time, and punch type

### Option 2: Export to Excel

```bash
cd testRun
python export_to_excel.py
```

This will:

- ✅ Fetch all attendance records from the device
- ✅ Export to `attendance_export_YYYYMMDD_HHMMSS.xlsx`
- ✅ Create formatted Excel file with proper columns

### Option 3: Start the API Server with Auto-Sync

```bash
python -m uvicorn app.main:app --reload
```

The attendance sync scheduler will:

- ✅ Run every 10 minutes automatically
- ✅ Fetch new records from ZK device
- ✅ Store in database with `synced_at` timestamp
- ✅ Track sync status via `/api/v1/sync/status` endpoint

## Configuration

### Device Settings

Edit `app/background/zkt_connector.py` or set environment variables:

```python
# Default values used if not provided:
DEVICE_IP = "172.16.32.184"      # ZK Machine IP
DEVICE_PORT = 4370               # ZK Machine Port (standard)
TIMEOUT = 20                      # Connection timeout in seconds
```

Or use environment variable:

```bash
export ZKT_MACHINE_IP="172.16.32.184"
```

## Data Flow

```
ZK Device
    ↓
ZKTConnector.get_attendance_records()
    ↓
Fetch users + attendance logs using pyzk
    ↓
Format records to {employee_id, name, date, time, punch}
    ↓
AttendanceSyncScheduler._perform_sync()
    ↓
AttendanceCreate schema validation
    ↓
Database storage with synced_at timestamp
```

## API Endpoints

### Get Sync Status

```bash
GET /api/v1/sync/status
```

Response:

```json
{
  "is_running": true,
  "last_sync_time": "2026-03-07T10:30:00",
  "next_sync_time": "2026-03-07T10:40:00",
  "total_synced": 254,
  "sync_count": 5,
  "last_error": null
}
```

### Manual Sync

```bash
POST /api/v1/sync/manual
```

### Get Attendance Records

```bash
GET /api/v1/attendance/?employee_id=123&attendance_date=2026-03-07
```

## Troubleshooting

### ❌ Connection Failed

1. Check device IP: `172.16.32.184`
2. Check device port: `4370`
3. Verify device is powered on
4. Check network connectivity: `ping 172.16.32.184`

### ❌ Empty Records

1. Ensure employees exist on the device
2. Check if device has attendance logs
3. Verify date filtering isn't excluding all records
4. Check server logs: `docker logs backend`

### ❌ Sync Not Running

1. Check if sync scheduler is started
2. Verify database connection is working
3. Check API logs for errors
4. Restart the application

## Important Notes

1. **Record Format**: The connector now returns proper Python `time` objects (not datetime) for `attendance_time`
2. **Punch Type**: Stored as boolean (True=IN, False=OUT), not as strings
3. **Sync Status**: Every synced record includes `synced_at` timestamp
4. **Device State**: Device is temporarily disabled during data fetch to prevent conflicts
5. **Incremental Sync**: Only fetches records since last sync time to avoid duplicates

## Files Modified

- ✅ `app/background/zkt_connector.py` - Complete rewrite to use pyzk
- ✅ `testRun/main.py` - Updated test script
- ✅ `testRun/export_to_excel.py` - New Excel export utility

## Dependencies

Required packages (already installed):

- `pyzk==0.9` - ZK device communication
- `openpyxl==3.1.5` - Excel export
- `FastAPI==0.129.0` - API framework
- `SQLAlchemy==2.0.46` - Database ORM

## Next Steps

1. Run the test script to verify connection works
2. Monitor the API `/sync/status` endpoint to see sync progress
3. Check database for attendance records appearing
4. Adjust sync interval if needed in `app/background/sync_scheduler.py` (default: 10 minutes)
