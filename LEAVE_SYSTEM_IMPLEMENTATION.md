# Leave Management System - Implementation Guide

## Overview

Complete Leave Management CRUD and API system with the following features:

✅ **Leave Cycles** - Create and manage leave years
✅ **Leave Types** - Define different leave types (Sick, Casual, Annual, etc.) with gender-specific rules
✅ **Employee Leave Records** - Allocate leaves to employees with tracking of used/pending days
✅ **Leave Applications** - Employees apply, HR/Managers review and approve/reject
✅ **Leave Summary/Dashboard** - View remaining leaves and statistics

---

## Integration Steps

### 1. Include the Leave Router in Main Application

Edit `app/main.py`:

```python
from fastapi import FastAPI
from app.api.v1 import leaves  # New import

app = FastAPI()

# Include the leaves router
app.include_router(leaves.router)
```

### 2. API Endpoints Summary

#### **LEAVE CYCLES**

```
POST   /api/v1/leaves/cycles                  - Create cycle
GET    /api/v1/leaves/cycles                  - Get all cycles
GET    /api/v1/leaves/cycles/active           - Get active cycle
GET    /api/v1/leaves/cycles/{cycle_id}       - Get specific cycle
PATCH  /api/v1/leaves/cycles/{cycle_id}       - Update cycle
DELETE /api/v1/leaves/cycles/{cycle_id}       - Delete cycle
```

#### **LEAVE TYPES**

```
POST   /api/v1/leaves/types                   - Create leave type
GET    /api/v1/leaves/types                   - Get all types
GET    /api/v1/leaves/types/cycle/{cycle_id}  - Get types for cycle
GET    /api/v1/leaves/types/{type_id}         - Get specific type
PATCH  /api/v1/leaves/types/{type_id}         - Update type
DELETE /api/v1/leaves/types/{type_id}         - Delete type
```

#### **EMPLOYEE LEAVE RECORDS**

```
POST   /api/v1/leaves/records                      - Create record
GET    /api/v1/leaves/records/employee/{emp_id}   - Get employee records
GET    /api/v1/leaves/records/me                   - Get my records
GET    /api/v1/leaves/records/{record_id}         - Get specific record
PATCH  /api/v1/leaves/records/{record_id}         - Update record
DELETE /api/v1/leaves/records/{record_id}         - Delete record
```

#### **LEAVE APPLICATIONS**

```
POST   /api/v1/leaves/applications                        - Apply for leave
GET    /api/v1/leaves/applications                        - Get all applications (HR)
GET    /api/v1/leaves/applications/pending                - Get pending (HR)
GET    /api/v1/leaves/applications/employee/{emp_id}     - Get employee's applications
GET    /api/v1/leaves/applications/me                     - Get my applications
GET    /api/v1/leaves/applications/{app_id}              - Get specific application
PATCH  /api/v1/leaves/applications/{app_id}              - Update application
POST   /api/v1/leaves/applications/{app_id}/approve      - Approve (HR)
POST   /api/v1/leaves/applications/{app_id}/reject       - Reject (HR)
POST   /api/v1/leaves/applications/{app_id}/cancel       - Cancel
DELETE /api/v1/leaves/applications/{app_id}              - Delete (HR)
```

#### **SUMMARY & DASHBOARD**

```
GET    /api/v1/leaves/summary/employee/{emp_id}  - Employee's leave summary
GET    /api/v1/leaves/summary/me                  - My leave summary
GET    /api/v1/leaves/dashboard/stats             - Leave statistics (HR)
```

---

## Example API Usage

### 1. Create a Leave Cycle

```bash
POST /api/v1/leaves/cycles
Content-Type: application/json

{
  "name": "2024-2025",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "is_active": true
}
```

### 2. Create Leave Types

```bash
POST /api/v1/leaves/types
Content-Type: application/json

{
  "cycle_id": 1,
  "name": "Sick Leave",
  "gender_specific": "ALL",
  "is_paid": true,
  "min_days": 1,
  "max_per_use": 3,
  "total_per_cycle": 12
}
```

### 3. Allocate Leaves to Employee

```bash
POST /api/v1/leaves/records
Content-Type: application/json

{
  "employee_id": 5,
  "leave_type_id": 1,
  "cycle_id": 1,
  "total_allocated": 12,
  "used_days": 0,
  "pending_days": 0
}
```

### 4. Employee Applies for Leave

```bash
POST /api/v1/leaves/applications
Content-Type: application/json

{
  "employee_id": 5,
  "leave_type_id": 1,
  "cycle_id": 1,
  "employee_record_id": 1,
  "start_date": "2024-02-15",
  "end_date": "2024-02-17",
  "requested_days": 3,
  "employee_note": "Medical appointment"
}
```

### 5. HR/Manager Approves Leave

```bash
POST /api/v1/leaves/applications/1/approve
Content-Type: application/json

{
  "status": "APPROVED",
  "reviewed_by": 2,
  "hr_note": "Approved - valid medical reason"
}
```

### 6. Check Employee's Leave Balance

```bash
GET /api/v1/leaves/summary/me
```

Response:

```json
{
  "employee_id": 5,
  "leaves_summary": [
    {
      "record_id": 1,
      "leave_type": "Sick Leave",
      "total_allocated": 12,
      "used_days": 3,
      "pending_days": 0,
      "remaining": 9
    }
  ]
}
```

---

## Frontend Widgets/Components

### 1. Leave Application Form Widget

```python
# Frontend component example (React/Vue)
class LeaveApplicationWidget:
    - Employee selector (auto-filled with current user)
    - Leave type dropdown (populated from API)
    - Date range picker (start_date, end_date)
    - Automatically calculate requested_days
    - Show current balance before submission
    - Comment/note textarea
    - Submit button
    - Real-time validation
```

### 2. Leave Balance Widget

```python
# Shows employee's leave status
class LeaveBalanceWidget:
    - Total allocated days
    - Used days (progress bar)
    - Pending days
    - Remaining days (highlighted)
    - Break down by leave type
    - Visual progress indicators
```

### 3. Applications Dashboard (HR/Manager)

```python
# For HR and managers to review applications
class LeaveApplicationDashboard:
    - Tabs: Pending | Approved | Rejected | All
    - Table with employee name, dates, status
    - Batch approve/reject actions
    - Filter by employee, date range, status
    - Click to review details
    - Add approval comments
    - Print/export functionality
```

### 4. Leave Configuration Panel (Admin)

```python
# For admin to setup leave system
class LeaveConfigPanel:
    - Create/edit leave cycles
    - Create/edit leave types
    - Configure gender-specific rules
    - Set leave quotas
    - Bulk allocate leaves to employees
    - View circular summaries
```

---

## Database Models Relationships

```
LeavesCycle (1) ──<< (Many) ─→ LeaveType
                              ├── (1) ──<< (Many) ─→ EmployeeLeaveRecord
                              └── (1) ──<< (Many) ─→ LeaveTransaction

Employee (1) ──<< (Many) ─→ EmployeeLeaveRecord
           ├──<< (Many) ─→ LeaveTransaction
           └── (as reviewed_by) ──<< (Many) ─→ LeaveTransaction
```

---

## Role-Based Permissions

### Employee

- ✅ View own leave records
- ✅ View own applications
- ✅ Create new leave application
- ✅ Update/cancel own pending applications
- ❌ Cannot approve other people's leaves
- ❌ Cannot modify leave allocations

### Manager/Team Lead

- ✅ View team's leave records
- ✅ View team's applications
- ✅ Approve/reject team's applications
- ❌ Cannot delete records (HR only)
- ❌ Cannot create/modify leave types

### HR/Admin

- ✅ Full access to all operations
- ✅ Create/modify leave cycles
- ✅ Create/modify leave types
- ✅ Allocate/modify employee leaves
- ✅ Approve/reject any application
- ✅ Delete records (with caution)
- ✅ View all dashboards

---

## Helper Functions

### Get Employee Leave Summary

```python
# Returns all leave types and remaining days for an employee
summary = get_employee_leaves_summary(db, employee_id, cycle_id=None)
# Returns: [
#   {
#     "leave_type": "Sick Leave",
#     "total_allocated": 12,
#     "used_days": 3,
#     "pending_days": 2,
#     "remaining": 7
#   },
#   ...
# ]
```

### Calculate Leave Duration

```python
# In your leave application, calculate days automatically:
from datetime import datetime
requested_days = (end_date - start_date).days + 1
```

---

## Error Handling

| Error                         | Status Code | Cause                              |
| ----------------------------- | ----------- | ---------------------------------- |
| `Insufficient leave balance`  | 400         | Employee used/pending > allocated  |
| `Leave cycle not found`       | 404         | Invalid cycle_id                   |
| `Leave record not found`      | 404         | Invalid record_id                  |
| `Leave application not found` | 404         | Invalid application_id             |
| `Cannot cancel non-pending`   | 400         | Trying to cancel approved/rejected |
| `Not allowed to update`       | 403         | Permission denied                  |

---

## Important Notes

1. **Automatic Leave Deduction**: When application is APPROVED, `used_days` is automatically incremented from `EmployeeLeaveRecord`
2. **Pending Days**: Tracks days in pending applications. Deducted only when approved
3. **Computed Field**: `remaining = total_allocated - used_days - pending_days` (auto-calculated)
4. **Timezone Aware**: All datetime fields use timezone-aware datetimes
5. **Foreign Keys**: Cascading deletes configured for proper data cleanup

---

## Testing Workflow

1. Create leave cycle (2024)
2. Create leave types (Sick, Annual, Casual)
3. Allocate leaves to employees
4. Employee applies for leave
5. HR/Manager reviews and approves
6. Check updated leave balance
7. Employee can see remaining days in dashboard

---

## Next Steps

1. Add role-based access control decorators to API endpoints
2. Add email notifications for approvals/rejections
3. Create batch upload for employee leave allocations
4. Add leave overlap detection (prevent double booking)
5. Implement holiday calendar integration
6. Add leave rollover logic for next cycle
7. Create audit logging for all leave changes
