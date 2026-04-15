# Leave Management System - Quick Reference & Examples

## Base URL

```
http://localhost:8000/api/v1/leave
```

---

## 🎯 Use Case 1: HR Creates Leave Configuration

### Step 1: Create a Leave Cycle

```bash
curl -X POST http://localhost:8000/api/v1/leave/cycles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "2024 Calendar Year",
    "start_month": 1,
    "start_day": 1,
    "end_month": 12,
    "end_day": 31
  }'
```

**Response:** `cycle_id: 1`

### Step 2: Create Leave Types

```bash
# Casual Leave - 12 days, can carry forward 5 days
curl -X POST http://localhost:8000/api/v1/leave/types \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Casual Leave",
    "is_paid": true,
    "max_per_cycle": 12,
    "carry_forward": true,
    "max_carry_forward": 5,
    "leave_cycle_id": 1
  }'
# Response: leave_type_id: 1

# Sick Leave - 10 days, NO carry forward
curl -X POST http://localhost:8000/api/v1/leave/types \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sick Leave",
    "is_paid": true,
    "max_per_cycle": 10,
    "carry_forward": false,
    "max_carry_forward": 0,
    "leave_cycle_id": 1
  }'
# Response: leave_type_id: 2

# Unpaid Leave - Unlimited
curl -X POST http://localhost:8000/api/v1/leave/types \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Unpaid Leave",
    "is_paid": false,
    "max_per_cycle": 0,
    "carry_forward": false,
    "max_carry_forward": 0,
    "leave_cycle_id": 1
  }'
# Response: leave_type_id: 3
```

### Step 3: Allocate Leave Balances to Employee

```bash
# Allocate 12 casual leaves to employee 5
curl -X POST "http://localhost:8000/api/v1/leave/allocate?employee_id=5&leave_type_id=1&allocated_days=12&cycle_start_date=2024-01-01&cycle_end_date=2024-12-31"

# Allocate 10 sick leaves to employee 5
curl -X POST "http://localhost:8000/api/v1/leave/allocate?employee_id=5&leave_type_id=2&allocated_days=10&cycle_start_date=2024-01-01&cycle_end_date=2024-12-31"

# Allocate carry forward from last year
curl -X POST "http://localhost:8000/api/v1/leave/adjust-carry-forward?employee_id=5&leave_type_id=1&cycle_start_date=2024-01-01&carry_forward_days=3"
```

---

## 🎯 Use Case 2: Employee Applies for Leave

### Current Status

- Employee 5 has:
  - Casual Leave: 12 allocated + 3 carry forward = 15 total
  - Used: 0, Pending: 0

### Step 1: Check Current Balance

```bash
curl http://localhost:8000/api/v1/leave/balance
# Response shows: remaining: 15 for casual leave
```

### Step 2: Apply for Leave

```bash
curl -X POST http://localhost:8000/api/v1/leave/apply \
  -H "Content-Type: application/json" \
  -d '{
    "leave_type_id": 1,
    "start_date": "2024-04-15",
    "end_date": "2024-04-18",
    "reason": "Planned family trip",
    "is_half_day": false
  }'

# Response:
# {
#   "id": 1,
#   "employee_id": 5,
#   "leave_type_id": 1,
#   "days": 4,          // 4 days total
#   "status": "pending",
#   "created_at": "2024-04-10T10:30:00"
# }
```

### Step 3: Check Updated Balance

```bash
curl http://localhost:8000/api/v1/leave/balance/1

# Response:
# {
#   "allocated": 12,
#   "carry_forward": 3,
#   "used": 0,
#   "pending": 4,       // 4 days pending approval
#   "remaining": 11     // 12 + 3 - 0 - 4 = 11
# }
```

### Step 4: View Leave Request Status

```bash
curl http://localhost:8000/api/v1/leave/my

# Response:
# [
#   {
#     "id": 1,
#     "start_date": "2024-04-15",
#     "end_date": "2024-04-18",
#     "days": 4,
#     "status": "pending",
#     "reason": "Planned family trip",
#     "approved_by": null,
#     "approved_at": null
#   }
# ]
```

---

## 🎯 Use Case 3: Manager Approves Leave

### Step 1: Manager Views Pending Requests

```bash
curl http://localhost:8000/api/v1/leave/pending

# Response:
# [
#   {
#     "id": 1,
#     "employee_id": 5,
#     "start_date": "2024-04-15",
#     "end_date": "2024-04-18",
#     "days": 4,
#     "status": "pending",
#     "reason": "Planned family trip"
#   }
# ]
```

### Step 2A: Approve Leave

```bash
curl -X POST http://localhost:8000/api/v1/leave/1/action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve"
  }'

# Response:
# {
#   "id": 1,
#   "status": "approved",
#   "approved_by": 3,  // Manager ID
#   "approved_at": "2024-04-10T15:45:00"
# }
```

### Step 2B: Or Reject Leave

```bash
curl -X POST http://localhost:8000/api/v1/leave/1/action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "reject"
  }'

# Response:
# {
#   "id": 1,
#   "status": "rejected",
#   "approved_by": 3,
#   "approved_at": "2024-04-10T15:45:00"
# }
```

### Step 3: Check Updated Balance (After Approval)

```bash
curl http://localhost:8000/api/v1/leave/balance/1

# Response:
# {
#   "allocated": 12,
#   "carry_forward": 3,
#   "used": 4,         // 4 days now USED (approved)
#   "pending": 0,      // No more pending
#   "remaining": 11    // 12 + 3 - 4 - 0 = 11
# }
```

---

## 🎯 Use Case 4: Employee Cancels Leave

### Condition: Only works if leave is in PENDING status

```bash
curl -X POST http://localhost:8000/api/v1/leave/1/cancel

# This will:
# 1. Change status to "cancelled"
# 2. Reduce pending days count
# 3. Return balance to available

# Response:
# {
#   "id": 1,
#   "status": "cancelled",
#   ...
# }
```

---

## 🎯 Use Case 5: Admin Views Employee Leave History

### View All Leaves for Employee

```bash
curl "http://localhost:8000/api/v1/leave/employee/5"

# Apply filters:
curl "http://localhost:8000/api/v1/leave/employee/5?status=approved"
curl "http://localhost:8000/api/v1/leave/employee/5?status=pending"
```

### View Employee Leave Balance

```bash
curl http://localhost:8000/api/v1/leave/employee/5/balance

# Response:
# [
#   {
#     "leave_type_id": 1,
#     "allocated": 12,
#     "used": 4,
#     "pending": 0,
#     "carry_forward": 3,
#     "remaining": 11
#   },
#   {
#     "leave_type_id": 2,
#     "allocated": 10,
#     "used": 0,
#     "pending": 0,
#     "carry_forward": 0,
#     "remaining": 10
#   }
# ]
```

### View Employee Summary

```bash
curl http://localhost:8000/api/v1/leave/employee/5/summary

# Response:
# [
#   {
#     "leave_type": "Casual Leave",
#     "allocated": 12,
#     "used": 4,
#     "pending": 0,
#     "carry_forward": 3,
#     "remaining": 11
#   },
#   {
#     "leave_type": "Sick Leave",
#     "allocated": 10,
#     "used": 0,
#     "pending": 0,
#     "carry_forward": 0,
#     "remaining": 10
#   }
# ]
```

---

## 🎯 Use Case 6: HR Department Report

### Get Leave Statistics

```bash
# All leaves by status
curl http://localhost:8000/api/v1/leave/stats/by-status

# Response:
# {
#   "pending": 3,
#   "approved": 45,
#   "rejected": 2,
#   "cancelled": 1
# }

# Filter by specific status
curl "http://localhost:8000/api/v1/leave/stats/by-status?status=pending"

# Response:
# {
#   "status": "pending",
#   "count": 3
# }
```

### Department Report

```bash
curl http://localhost:8000/api/v1/leave/stats/department/1

# Response:
# {
#   "department_id": 1,
#   "total_employees": 25,
#   "total_leaves": 45,
#   "pending": 3,
#   "approved": 40,
#   "rejected": 2
# }
```

---

## 🚨 Error Scenarios

### Error 1: Insufficient Leave Balance

```bash
curl -X POST http://localhost:8000/api/v1/leave/apply \
  -H "Content-Type: application/json" \
  -d '{
    "leave_type_id": 1,
    "start_date": "2024-04-15",
    "end_date": "2024-05-20",  # 36 days, but only 11 available
    "reason": "Too long",
    "is_half_day": false
  }'

# Response: 400 Bad Request
# {
#   "detail": "Insufficient leave balance. Available: 11, Requested: 36"
# }
```

### Error 2: Leave Overlap

```bash
# Try to apply when already have pending leave for same dates
curl -X POST http://localhost:8000/api/v1/leave/apply \
  -H "Content-Type: application/json" \
  -d '{
    "leave_type_id": 1,
    "start_date": "2024-04-15",  # Same as previous leave!
    "end_date": "2024-04-16",
    "reason": "Overlapping",
    "is_half_day": false
  }'

# Response: 400 Bad Request
# {
#   "detail": "Leave already exists for selected dates"
# }
```

### Error 3: Invalid Leave Type

```bash
curl -X POST http://localhost:8000/api/v1/leave/apply \
  -H "Content-Type: application/json" \
  -d '{
    "leave_type_id": 999,  # Non-existent
    "start_date": "2024-04-15",
    "end_date": "2024-04-18",
    "reason": "Invalid type",
    "is_half_day": false
  }'

# Response: 404 Not Found
# {
#   "detail": "Leave type not found"
# }
```

### Error 4: Cancel Approved Leave

```bash
# Cannot cancel leaves that are already approved
# Only works with "pending" status leaves

curl -X POST http://localhost:8000/api/v1/leave/1/cancel

# If leave is already approved:
# Response: 400 Bad Request
# (Depends on implementation logic)
```

---

## 📊 Balance Calculation Formula

```
Remaining Balance = Allocated + CarryForward - Used - Pending

Example:
- Allocated:      12 days
- Carry Forward:   3 days (from previous year)
- Used:            4 days (approved & taken)
- Pending:         2 days (awaiting approval)
- Remaining:       9 days (12 + 3 - 4 - 2)

When leave is APPROVED:
- Pending moves to Used
- Remaining decreases

When leave is REJECTED:
- Pending is removed
- Remaining increases
```

---

## 🔑 Key Status Transitions

```
Leave Status Flow:

             Employee Applies
                    ↓
              PENDING (awaiting approval)
             /                 \
        Manager Approves    Manager Rejects
            ↓                      ↓
        APPROVED              REJECTED
            ↓
        Employee Can Cancel → CANCELLED
            ↓
        CANCELLED (final)

Balance Impact:
PENDING:   pending balance increases
APPROVED:  pending → used
REJECTED:  pending → removed
CANCELLED: reverses the pending/used impact
```

---

## 🔐 TODO: Authentication Setup

Replace hardcoded values in endpoints:

```python
# Before (Development)
employee_id: int = 1,  # Hardcoded

# After (Production)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Validate token
    # Return user
    pass

# In endpoint:
employee_id: int = Depends(get_current_user),
```

---

## 📌 Useful Queries

### Get count of approved leaves this month

```bash
# Query: All leaves with status="approved" and start_date in April 2024
GET /api/v1/leave/stats/by-status?status=approved

# Then filter in application by month
```

### Get employees with low leave balance

```bash
# Query: All employees with remaining < 2 days
# This requires a custom endpoint or post-processing
```

### Export leave data to Excel

```bash
# GET /api/v1/leave/employee/{employee_id}
# Get all leaves, then use pandas/openpyxl to export
```

---

## 🎓 Testing Checklist

- [ ] Create leave cycle
- [ ] Create leave types (Casual, Sick, Unpaid)
- [ ] Allocate leaves to employee
- [ ] Employee applies for 4-day casual leave
- [ ] Check pending balance decreased
- [ ] Manager approves leave
- [ ] Check used balance increased
- [ ] Employee cancels another pending leave
- [ ] Check overlap validation works
- [ ] Check insufficient balance error
- [ ] Get department statistics
- [ ] Test different carry forward scenarios
