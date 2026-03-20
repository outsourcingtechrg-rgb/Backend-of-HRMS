# Raw Attendance & Manual Linking Guide

## Overview

The system now pulls **ALL** attendance records from the ZKT device and stores them **without linking to employees**. You can then manually link them to employees when ready.

### Workflow

```
1. ZKT Device
   ↓
2. Sync Service (every 5 minutes)
   ↓
3. Raw Attendance Table
   - machine_user_id (from device)
   - employee_name (from device)
   - attendance_date
   - attendance_time
   - punch (in/out)
   ↓
4. Manual Linking (API endpoint)
   - Link raw records to employee IDs
   ↓
5. Attendance Records
   - Now linked to real employees
```

## Setup

### Step 1: Run Migration
```bash
alembic upgrade head
```

This creates the `raw_attendance` table.

### Step 2: Restart API
```bash
Ctrl+C  # Stop current server
uvicorn app.main:app --reload
```

The scheduler will automatically sync all raw attendance every 5 minutes.

## API Endpoints

### 1. Get All Raw Attendance
```bash
GET /api/v1/attendance/raw
```

Query parameters:
- `machine_user_id` - Filter by ZKT device user ID
- `from_date` - Start date (YYYY-MM-DD)
- `to_date` - End date (YYYY-MM-DD)
- `linked` - `true`=linked only, `false`=unlinked only, `null`/empty=all
- `limit` - Max records (default 100, max 1000)
- `skip` - Pagination offset

**Example:**
```bash
# Get first 100 unlinked records
curl "http://localhost:8000/api/v1/attendance/raw?linked=false&limit=100"

# Get records for machine user ID 5
curl "http://localhost:8000/api/v1/attendance/raw?machine_user_id=5"

# Get records between dates
curl "http://localhost:8000/api/v1/attendance/raw?from_date=2026-01-01&to_date=2026-03-14"
```

**Response:**
```json
{
  "total": 500,
  "skip": 0,
  "limit": 100,
  "count": 100,
  "data": [
    {
      "id": 1,
      "machine_user_id": 5,
      "employee_name": "John Doe",
      "attendance_date": "2026-03-14",
      "attendance_time": "08:30:00",
      "punch": true,
      "employee_id": null,
      "linked_at": null,
      "synced_at": "2026-03-14T10:45:00"
    }
  ]
}
```

### 2. Link Single Record to Employee
```bash
POST /api/v1/attendance/raw/{raw_attendance_id}/link
```

**Request:**
```json
{
  "employee_id": 10
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/attendance/raw/1/link \
  -H "Content-Type: application/json" \
  -d '{"employee_id": 10}'
```

### 3. Link ALL Records for Machine User ID
```bash
POST /api/v1/attendance/raw/link-by-machine-id
```

This links **all unlinked** records for a specific ZKT machine user to an employee.

**Request:**
```json
{
  "machine_user_id": 5,
  "employee_id": 10
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/attendance/raw/link-by-machine-id \
  -H "Content-Type: application/json" \
  -d '{
    "machine_user_id": 5,
    "employee_id": 10
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Linked 250 records to employee John Smith",
  "linked_count": 250,
  "machine_user_id": 5,
  "employee_id": 10
}
```

### 4. Link Multiple Records (Bulk)
```bash
POST /api/v1/attendance/raw/link-multiple
```

**Request:**
```json
{
  "links": [
    {"raw_attendance_id": 1, "employee_id": 10},
    {"raw_attendance_id": 2, "employee_id": 10},
    {"raw_attendance_id": 3, "employee_id": 11}
  ]
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/attendance/raw/link-multiple \
  -H "Content-Type: application/json" \
  -d '{
    "links": [
      {"raw_attendance_id": 1, "employee_id": 10},
      {"raw_attendance_id": 2, "employee_id": 10},
      {"raw_attendance_id": 100, "employee_id": 15}
    ]
  }'
```

### 5. Get Raw Attendance Summary
```bash
GET /api/v1/attendance/raw/summary
```

**Response:**
```json
{
  "total_records": 5000,
  "linked": 2500,
  "unlinked": 2500,
  "unique_machine_users": 50,
  "link_percentage": 50.0
}
```

### 6. Trigger Manual Sync
```bash
POST /api/v1/attendance/sync/raw-data
```

Manually trigger the sync service to pull latest data from ZKT device.

**Response:**
```json
{
  "success": true,
  "message": "Raw attendance sync completed",
  "data": {
    "inserted": 25,
    "records_received": 30,
    "skipped": 5,
    "last_synced_at": "2026-03-14T10:50:00"
  }
}
```

## Workflow Examples

### Example 1: Link Machine User 5 to Employee 10
```bash
# Get unlinked records for machine user 5
curl "http://localhost:8000/api/v1/attendance/raw?machine_user_id=5&linked=false"

# Link all to employee 10
curl -X POST http://localhost:8000/api/v1/attendance/raw/link-by-machine-id \
  -H "Content-Type: application/json" \
  -d '{"machine_user_id": 5, "employee_id": 10}'
```

### Example 2: Check Sync Progress
```bash
# Check summary
curl http://localhost:8000/api/v1/attendance/raw/summary

# Gets:
# - Total records synced
# - How many are linked
# - How many still need linking
# - Percentage complete
```

### Example 3: Bulk Link Records
```bash
# Build a list of links (machine_user_id → employee_id mapping)
# Then send bulk request
curl -X POST http://localhost:8000/api/v1/attendance/raw/link-multiple \
  -H "Content-Type: application/json" \
  -d '{
    "links": [
      {"raw_attendance_id": 1, "employee_id": 10},
      {"raw_attendance_id": 2, "employee_id": 10},
      {"raw_attendance_id": 3, "employee_id": 11},
      {"raw_attendance_id": 4, "employee_id": 12}
    ]
  }'
```

## Database Tables

### raw_attendance
```sql
SELECT * FROM raw_attendance WHERE employee_id IS NULL;  -- Unlinked
SELECT * FROM raw_attendance WHERE employee_id IS NOT NULL;  -- Linked
SELECT * FROM raw_attendance WHERE machine_user_id = 5;  -- For specific machine user
```

## How It Works

1. **Syncing (Automatic every 5 minutes)**
   - Queries ZKT device
   - Gets all attendance since last sync
   - Stores in `raw_attendance` table
   - Does NOT create or link employees

2. **Manual Linking**
   - User identifies which machine_user_id belongs to which employee
   - Calls linking endpoint to connect them
   - Records updated with `employee_id`, `linked_at`, `linked_by`

3. **After Linking**
   - Raw attendance records have employee_id filled
   - Can query by employee
   - Can generate reports by employee

## Benefits

✓ **No Data Loss** - All attendance captured
✓ **Time to Verify** - You control when to link
✓ **Flexibility** - Link in batches by department, date, etc.
✓ **Simple** - No placeholder employees or complex logic
✓ **Auditable** - Track when and who linked each record

## Common Tasks

### Find all unlinked records
```bash
curl "http://localhost:8000/api/v1/attendance/raw?linked=false"
```

### Link all records for a machine user
```bash
curl -X POST http://localhost:8000/api/v1/attendance/raw/link-by-machine-id \
  -H "Content-Type: application/json" \
  -d '{"machine_user_id": 5, "employee_id": 10}'
```

### Get records for a date range
```bash
curl "http://localhost:8000/api/v1/attendance/raw?from_date=2026-03-01&to_date=2026-03-14"
```

### See progress
```bash
curl http://localhost:8000/api/v1/attendance/raw/summary
```

## Data Storage

Each raw attendance record stores:
- **machine_user_id** - ZKT device user ID (always present)
- **employee_name** - Name from ZKT device
- **attendance_date** - When attendance occurred
- **attendance_time** - Time of punch
- **punch** - true=in, false=out
- **employee_id** - Filled when manually linked
- **linked_at** - When it was linked
- **linked_by** - How it was linked (manual, bulk, etc.)

## Next Steps

1. ✓ Run migration: `alembic upgrade head`
2. ✓ Restart API: `uvicorn app.main:app --reload`
3. ✓ Check sync: `curl http://localhost:8000/api/v1/attendance/raw/summary`
4. ✓ Link records: Use API endpoints to link to employees
5. ✓ Verify: Query by employee to see linked attendance

## Questions?

- **Why raw_attendance?** - To keep attendance data separate until you verify the links
- **Can I edit links?** - Currently the link endpoint updates. You can modify via SQL if needed.
- **What about historical data?** - Sync starts from last_synced_at (defaults to 2020-01-01 to get all)
- **How often does it sync?** - Every 5 minutes (configurable in scheduler.py)
