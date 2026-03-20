# Changes Summary - Attendance Sync System

## Problems Fixed

### 1. **AttendanceSync Model Schema Issue**

**File:** `app/models/attendanceSync.py`

**Problem:**

- Unused `synced_time` field (Integer, unclear purpose)
- No configurable sync interval
- No enable/disable capability
- Missing timestamps for tracking

**Solution:**

```python
# Before
class AttendanceSync(Base):
    device_ip = Column(String(255), unique=True, nullable=False)
    synced_time = Column(Integer, unique=False, nullable=False)  # ❌ Unused
    last_synced_at = Column(DateTime, ...)

# After
class AttendanceSync(Base):
    device_ip = Column(String(255), unique=True, nullable=False)
    last_synced_at = Column(DateTime, ...)                       # ✓ Keeps sync time
    sync_interval_minutes = Column(Integer, default=10)          # ✓ Configurable interval
    is_enabled = Column(Boolean, default=True)                  # ✓ Enable/disable sync
    created_at = Column(DateTime, ...)                          # ✓ Track created time
    updated_at = Column(DateTime, ...)                          # ✓ Track updates
```

### 2. **Attendance Sync Service Issues**

**File:** `app/background/attendance_sync_service.py`

**Problems:**

- Skipped missing employees instead of creating placeholders
- No FK reference creation (department, role, shift)
- Poor error handling and logging
- Manual sync mode without schedule

**Solutions:**

```python
# Added function to create defaults
def _get_or_create_defaults(db: Session):
    """Create default Department, Role, Shift for FK constraints"""
    # Creates if missing, returns IDs for use in placeholders

# Added placeholder creation logic
if not employee:
    # Create placeholder employee with all required FK references
    employee = Employee(
        employee_id=uid,
        f_name=f"emp_{uid}",
        email=f"emp_{uid}@hrms.internal",
        department_id=dept_id,    # ✓ FK reference
        role_id=role_id,          # ✓ FK reference
        shift_id=shift_id,        # ✓ FK reference
        status="placeholder"
    )

# Added comprehensive logging
logger.info(f"Fetched {len(records)} records from device")
logger.warning(f"Creating placeholder for employee {uid}")
logger.error(f"Error processing record: {e}")
```

### 3. **ZKT Connection Issues**

**File:** `app/background/zkteco.py`

**Problems:**

- Silently failing with `print("Error:")` instead of logging
- No visibility into what's happening
- Poor error categorization
- Could have connection state issues

**Solutions:**

- Added comprehensive logging at each step
- Better timestamp validation
- Try-catch for graceful disconnect
- Proper error messages for debugging

```python
logger.info(f"Connecting to ZKT device at {device_ip}:{port}")
logger.info("Connected to ZKT device successfully")
logger.info(f"Retrieved {len(user_map)} users from device")
logger.info(f"Processed {len(data)} new attendance records")
```

### 4. **Scheduler Not Using Database Settings**

**File:** `app/background/sync_scheduler.py`

**Problem:**

- Hardcoded 10-minute interval at initialization
- No way to change interval without restarting
- Can't disable sync without code changes
- Doesn't respect database configuration

**Solution:**
Added dynamic interval checking in `_sync_loop()`:

```python
# Read from database each cycle
sync_config = db.query(AttendanceSync).filter(
    AttendanceSync.device_ip == self.machine_ip
).first()

# Check if enabled
if not sync_config.is_enabled:
    logger.info("Sync is disabled in settings")
    continue

# Update interval if changed
if current_interval != self.sync_interval:
    self.sync_interval = current_interval
```

### 5. **No API for Managing Settings**

**File:** `app/api/v1/attendance_sync.py`

**Before:** Only had:

- `POST /attendance-sync/run` - Manual sync
- `GET /attendance-sync/status` - Basic status

**After:** Now has:

- `GET /api/v1/attendance-sync/status` - Get detailed settings
- `PATCH /api/v1/attendance-sync/settings` - Update interval/enabled
- `POST /api/v1/attendance-sync/run` - Manual sync
- `POST /api/v1/attendance-sync/reset-sync-time` - Load all historical data

## New Features Added

### 1. **Configurable Sync Interval**

```bash
# Change to sync every 5 minutes
PATCH /api/v1/attendance-sync/settings
{
    "sync_interval_minutes": 5,
    "is_enabled": true
}
```

### 2. **Enable/Disable Sync**

```bash
# Disable sync temporarily
PATCH /api/v1/attendance-sync/settings
{
    "is_enabled": false
}
```

### 3. **Load Historical Data**

```bash
# Reset to 2020 and sync all records
POST /api/v1/attendance-sync/reset-sync-time
POST /api/v1/attendance-sync/run
```

### 4. **Detailed Status Information**

```bash
GET /api/v1/attendance-sync/status
# Returns:
# - Current interval
# - Enable/disable status
# - Last sync time
# - Created/updated timestamps
```

## Files Created

1. **`app/schemas/sync_settings.py`**
   - Pydantic schemas for API requests/responses
   - SyncSettingsRead, SyncSettingsCreate, SyncSettingsUpdate

2. **`init_sync_system.py`**
   - Setup script to initialize database
   - Creates default Department, Role, Shift
   - Creates sync settings record
   - Verifies all tables exist

3. **`alembic/versions/update_attendance_sync_schema.py`**
   - Database migration for schema update
   - Run with: `alembic upgrade head`

4. **`SCHEDULER_CONFIGURATION_GUIDE.md`**
   - Comprehensive configuration documentation
   - API endpoint details
   - Workflow examples
   - Troubleshooting guide

5. **`SCHEDULER_SETUP.md`**
   - Installation and setup instructions
   - Step-by-step configuration
   - Performance considerations
   - Monitoring and logging

## Setup Instructions

### Step 1: Database Migration

```bash
alembic upgrade head
```

### Step 2: Initialize System

```bash
python init_sync_system.py
```

Output:

```
✓ Sync settings created successfully
✓ Default Department created
✓ Default Role created
✓ Default Shift created
```

### Step 3: Start API

```bash
uvicorn app.main:app --reload
```

### Step 4: Verify

```bash
curl http://localhost:8000/api/v1/attendance-sync/status
```

### Step 5: Load Data

```bash
# Reset sync to get all historical data
curl -X POST http://localhost:8000/api/v1/attendance-sync/reset-sync-time

# Trigger sync
curl -X POST http://localhost:8000/api/v1/attendance-sync/run
```

## Configuration Workflow

```
1. System starts
   ↓
2. Sync scheduler reads interval from database
   ↓
3. Checks is_enabled flag
   ↓
4. If enabled, fetches attendance from ZKT device
   ↓
5. Creates placeholder employees for missing IDs
   ↓
6. Inserts attendance records
   ↓
7. Updates last_synced_at timestamp
   ↓
8. Waits sync_interval_minutes
   ↓
9. Repeats from step 2
```

## API Endpoints Reference

| Method | Endpoint                                  | Purpose                  |
| ------ | ----------------------------------------- | ------------------------ |
| GET    | `/api/v1/attendance-sync/status`          | Get current settings     |
| PATCH  | `/api/v1/attendance-sync/settings`        | Update interval/enabled  |
| POST   | `/api/v1/attendance-sync/run`             | Manual sync trigger      |
| POST   | `/api/v1/attendance-sync/reset-sync-time` | Load all historical data |

## Data Now Persisted With

- **Device IP:** 172.16.32.184
- **Port:** 4370
- **Sync Interval:** 10 minutes (configurable)
- **Auto-retry:** Every 10 minutes on failure
- **Max errors:** 5 consecutive before warning
- **Placeholder emails:** emp_X@hrms.internal
- **Default FK values:**
  - Department: "Placeholder Department"
  - Role: Level 1 "Staff"
  - Shift: 09:00-17:00 (8 hours)

## Logging Improvements

Now logs:

- Device connection status
- Users fetched from device
- Records fetched from device
- Missing employees found
- Placeholder employees created
- Attendance records inserted
- Sync duration and statistics
- Any errors with full context

Example log output:

```
INFO - Starting scheduled attendance sync...
INFO - Last sync: 2026-03-14 10:30:00
INFO - Fetched 50 records from device
WARNING - Creating 5 placeholder employee records
INFO - Sync completed: 45 inserted, 50 total, 5 skipped
```

## What's Now Configurable

✓ Sync interval (minutes)
✓ Enable/disable sync
✓ Last sync time (for historical data loading)
✓ Device-specific settings

## What Still Needs Configuration

- Device IP: 172.16.32.184 (in multiple files, could move to env vars)
- Port: 4370 (in multiple files, could move to env vars)
- Default timezone handling
- Multiple device support

## Testing

After setup, test with:

```bash
# 1. Check status
curl http://localhost:8000/api/v1/attendance-sync/status

# 2. Manually sync
curl -X POST http://localhost:8000/api/v1/attendance-sync/run

# 3. Change interval
curl -X PATCH http://localhost:8000/api/v1/attendance-sync/settings \
  -H "Content-Type: application/json" \
  -d '{"sync_interval_minutes": 5}'

# 4. Disable sync
curl -X PATCH http://localhost:8000/api/v1/attendance-sync/settings \
  -H "Content-Type: application/json" \
  -d '{"is_enabled": false}'

# 5. Load historical data
curl -X POST http://localhost:8000/api/v1/attendance-sync/reset-sync-time
```

## Version Control

All changes:

- ✓ Backward compatible
- ✓ Non-breaking to existing endpoints
- ✓ Database migration included
- ✓ Setup script idempotent (safe to run multiple times)

## Known Limitations

1. Device IP/Port hardcoded (can be moved to env vars)
2. Single device only (could support multiple with config table)
3. No authentication to ZKT device (standard on internal networks)
4. No historical sync resumption on crash (but will start from last_synced_at)
