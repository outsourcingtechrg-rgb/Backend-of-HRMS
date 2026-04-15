# Leave Management System - Complete API Documentation

## Overview

Complete HRMS Leave Management System with HR controls, employee applications, manager approvals, and comprehensive reporting.

---

## 🔐 Authentication & Authorization

⚠️ **Note:** Replace hardcoded `employee_id` and `approver_id` with actual authentication in production.

**To implement:**

- Add `Depends(get_current_user)` to protected endpoints
- Add role/permission checks (HR, Manager, Employee)

---

## 📋 Leave Masters (HR Configuration)

### 1. Leave Cycles Management

#### Create Leave Cycle

```
POST /api/v1/leave/cycles
Content-Type: application/json

{
    "name": "Jan-Dec",
    "start_month": 1,
    "start_day": 1,
    "end_month": 12,
    "end_day": 31
}

Response: 201 Created
{
    "id": 1,
    "name": "Jan-Dec",
    "start_month": 1,
    "start_day": 1,
    "end_month": 12,
    "end_day": 31,
    "is_active": true
}
```

#### Get All Leave Cycles

```
GET /api/v1/leave/cycles

Response: 200 OK
[
    {
        "id": 1,
        "name": "Jan-Dec",
        "start_month": 1,
        "start_day": 1,
        "end_month": 12,
        "end_day": 31,
        "is_active": true
    }
]
```

#### Get Specific Leave Cycle

```
GET /api/v1/leave/cycles/{cycle_id}

Response: 200 OK
{
    "id": 1,
    "name": "Jan-Dec",
    "start_month": 1,
    "start_day": 1,
    "end_month": 12,
    "end_day": 31,
    "is_active": true
}
```

#### Update Leave Cycle

```
PUT /api/v1/leave/cycles/{cycle_id}
Content-Type: application/json

{
    "name": "Jan-Dec 2024",
    "start_month": 1,
    "start_day": 1,
    "end_month": 12,
    "end_day": 31
}

Response: 200 OK
```

#### Deactivate Leave Cycle

```
POST /api/v1/leave/cycles/{cycle_id}/deactivate

Response: 200 OK
```

---

### 2. Leave Types Management

#### Create Leave Type with Limits

```
POST /api/v1/leave/types
Content-Type: application/json

{
    "name": "Casual Leave",
    "is_paid": true,
    "max_per_cycle": 12,
    "carry_forward": true,
    "max_carry_forward": 5,
    "leave_cycle_id": 1
}

Response: 201 Created
{
    "id": 1,
    "name": "Casual Leave",
    "is_paid": true,
    "max_per_cycle": 12,
    "carry_forward": true,
    "max_carry_forward": 5,
    "leave_cycle_id": 1
}
```

#### Get All Leave Types

```
GET /api/v1/leave/types

Response: 200 OK
[
    {
        "id": 1,
        "name": "Casual Leave",
        "is_paid": true,
        "max_per_cycle": 12,
        "carry_forward": true,
        "max_carry_forward": 5,
        "leave_cycle_id": 1
    },
    {
        "id": 2,
        "name": "Sick Leave",
        "is_paid": true,
        "max_per_cycle": 10,
        "carry_forward": false,
        "max_carry_forward": 0,
        "leave_cycle_id": 1
    }
]
```

#### Get Leave Types by Cycle

```
GET /api/v1/leave/cycles/{cycle_id}/types

Response: 200 OK
[{...leave types in cycle...}]
```

#### Update Leave Type Limits

```
PUT /api/v1/leave/types/{leave_type_id}
Content-Type: application/json

{
    "name": "Casual Leave",
    "is_paid": true,
    "max_per_cycle": 15,
    "carry_forward": true,
    "max_carry_forward": 5
}

Response: 200 OK
```

#### Delete Leave Type

```
DELETE /api/v1/leave/types/{leave_type_id}

Response: 200 OK
{
    "message": "Leave type deleted"
}
```

---

### 3. Leave Balance Allocation (HR)

#### Allocate Leave Balance to Employee

```
POST /api/v1/leave/allocate
?employee_id=102
&leave_type_id=1
&allocated_days=12
&cycle_start_date=2024-01-01
&cycle_end_date=2024-12-31

Response: 201 Created
{
    "id": 1,
    "employee_id": 102,
    "leave_type_id": 1,
    "leave_cycle_id": 1,
    "cycle_start_date": "2024-01-01",
    "cycle_end_date": "2024-12-31",
    "allocated": 12,
    "used": 0,
    "pending": 0,
    "carry_forward": 0,
    "remaining": 12
}
```

#### Adjust Carry Forward Leaves

```
POST /api/v1/leave/adjust-carry-forward
?employee_id=102
&leave_type_id=1
&cycle_start_date=2024-01-01
&carry_forward_days=3

Response: 200 OK
{
    "id": 1,
    "employee_id": 102,
    "leave_type_id": 1,
    "allocated": 12,
    "used": 0,
    "pending": 0,
    "carry_forward": 3,
    "remaining": 15
}
```

---

## 👥 Employee Endpoints

### 4. Apply for Leave

#### Submit Leave Request

```
POST /api/v1/leave/apply
Content-Type: application/json

{
    "leave_type_id": 1,
    "start_date": "2024-04-15",
    "end_date": "2024-04-18",
    "reason": "Personal reasons",
    "is_half_day": false
}

Response: 201 Created
{
    "id": 1,
    "employee_id": 5,
    "leave_type_id": 1,
    "leave_cycle_id": 1,
    "start_date": "2024-04-15",
    "end_date": "2024-04-18",
    "days": 4,
    "is_half_day": false,
    "reason": "Personal reasons",
    "status": "pending",
    "approved_by": null,
    "approved_at": null,
    "created_at": "2024-04-10T10:30:00"
}
```

#### View My Leave Requests

```
GET /api/v1/leave/my

Optional Query Parameters:
?status=pending (filter by status)

Response: 200 OK
[
    {
        "id": 1,
        "employee_id": 5,
        "leave_type_id": 1,
        "leave_cycle_id": 1,
        "start_date": "2024-04-15",
        "end_date": "2024-04-18",
        "days": 4,
        "is_half_day": false,
        "reason": "Personal reasons",
        "status": "pending",
        "approved_by": null,
        "approved_at": null,
        "created_at": "2024-04-10T10:30:00"
    }
]
```

### 5. Check Leave Balance

#### View All Leave Balances

```
GET /api/v1/leave/balance

Response: 200 OK
[
    {
        "id": 1,
        "employee_id": 5,
        "leave_type_id": 1,
        "leave_cycle_id": 1,
        "cycle_start_date": "2024-01-01",
        "cycle_end_date": "2024-12-31",
        "allocated": 12,
        "used": 2,
        "pending": 4,
        "carry_forward": 3,
        "remaining": 9
    },
    {
        "id": 2,
        "employee_id": 5,
        "leave_type_id": 2,
        "leave_cycle_id": 1,
        "cycle_start_date": "2024-01-01",
        "cycle_end_date": "2024-12-31",
        "allocated": 10,
        "used": 0,
        "pending": 0,
        "carry_forward": 0,
        "remaining": 10
    }
]
```

#### View Balance for Specific Leave Type

```
GET /api/v1/leave/balance/{leave_type_id}

Response: 200 OK
{
    "id": 1,
    "employee_id": 5,
    "leave_type_id": 1,
    "allocated": 12,
    "used": 2,
    "pending": 4,
    "carry_forward": 3,
    "remaining": 9
}
```

### 6. Cancel Leave Request

#### Cancel Own Leave

```
POST /api/v1/leave/{leave_id}/cancel

Response: 200 OK
{
    "id": 1,
    "employee_id": 5,
    "status": "cancelled",
    "start_date": "2024-04-15",
    "end_date": "2024-04-18",
    "days": 4,
    ...
}
```

---

## 👔 Manager Endpoints

### 7. Approve/Reject Leaves

#### Review Pending Leaves

```
GET /api/v1/leave/pending

Response: 200 OK
[
    {
        "id": 1,
        "employee_id": 5,
        "leave_type_id": 1,
        "start_date": "2024-04-15",
        "end_date": "2024-04-18",
        "days": 4,
        "reason": "Personal reasons",
        "status": "pending",
        "created_at": "2024-04-10T10:30:00"
    }
]
```

#### Approve/Reject Leave Request

```
POST /api/v1/leave/{leave_id}/action
Content-Type: application/json

{
    "action": "approve"  // or "reject"
}

Response: 200 OK
{
    "id": 1,
    "employee_id": 5,
    "status": "approved",
    "approved_by": 3,
    "approved_at": "2024-04-10T15:45:00",
    ...
}
```

---

## 🔧 Admin Endpoints

### 8. View Employee Leave Details

#### Get Employee All Leaves

```
GET /api/v1/leave/employee/{employee_id}

Optional Query Parameters:
?status=approved (filter by status)

Response: 200 OK
[
    {
        "id": 1,
        "employee_id": 5,
        "status": "approved",
        ...
    }
]
```

#### Get Employee Leave Balance

```
GET /api/v1/leave/employee/{employee_id}/balance

Response: 200 OK
[
    {
        "id": 1,
        "employee_id": 5,
        "leave_type_id": 1,
        "allocated": 12,
        "used": 2,
        "pending": 0,
        "carry_forward": 3,
        "remaining": 13
    }
]
```

#### Get Employee Leave Summary

```
GET /api/v1/leave/employee/{employee_id}/summary

Response: 200 OK
[
    {
        "leave_type": "Casual Leave",
        "allocated": 12,
        "used": 2,
        "pending": 0,
        "carry_forward": 3,
        "remaining": 13
    },
    {
        "leave_type": "Sick Leave",
        "allocated": 10,
        "used": 1,
        "pending": 2,
        "carry_forward": 0,
        "remaining": 7
    }
]
```

---

## 📊 Reports & Analytics

### 9. Leave Statistics

#### Get Leaves by Status

```
GET /api/v1/leave/stats/by-status

Optional Query Parameters:
?status=pending

Response: 200 OK (without status filter)
{
    "pending": 5,
    "approved": 23,
    "rejected": 2,
    "cancelled": 1
}

Response: 200 OK (with status filter)
{
    "status": "pending",
    "count": 5
}
```

#### Get Department Leave Statistics

```
GET /api/v1/leave/stats/department/{department_id}

Response: 200 OK
{
    "department_id": 1,
    "total_employees": 25,
    "total_leaves": 45,
    "pending": 5,
    "approved": 35,
    "rejected": 5
}
```

---

## 📝 Data Models & Constraints

### Leave Cycle

- Must have unique name
- Valid month range: 1-12
- Valid day range: 1-31
- Can be active/inactive

### Leave Type

- Must have unique name within system
- Paid/Unpaid flag
- Max days per cycle (e.g., 12)
- Carry forward settings (max days that can be carried)
- Linked to Leave Cycle

### Leave Balance

- Unique constraint: (employee_id, leave_type_id, cycle_start_date)
- Tracks: allocated, used, pending, carry_forward
- Remaining = allocated + carry_forward - used - pending

### Leave Request

- Start date must be ≤ End date
- Cannot overlap with existing pending/approved leaves
- Requires valid leave_type_id
- Status: pending → approved/rejected → cancelled
- Half-day = 0.5 days, full-day = days difference + 1

---

## ⚠️ Error Handling

### Common Error Responses

```
400 Bad Request
{
    "detail": "Insufficient leave balance. Available: 4, Requested: 5"
}

400 Bad Request
{
    "detail": "Leave already exists for selected dates"
}

404 Not Found
{
    "detail": "Leave type not found"
}

403 Forbidden
{
    "detail": "Unauthorized"
}
```

---

## 🚀 Sample Workflow

### HR Setup

1. Create leave cycle: `POST /api/v1/leave/cycles`
2. Create leave types: `POST /api/v1/leave/types`
3. Allocate balances: `POST /api/v1/leave/allocate`

### Employee Flow

1. Apply for leave: `POST /api/v1/leave/apply`
2. View status: `GET /api/v1/leave/my`
3. Check balance: `GET /api/v1/leave/balance`
4. Cancel (if pending): `POST /api/v1/leave/{id}/cancel`

### Manager Flow

1. View pending: `GET /api/v1/leave/pending`
2. Approve/Reject: `POST /api/v1/leave/{id}/action`

### Admin Flow

1. View employee leaves: `GET /api/v1/leave/employee/{id}`
2. View statistics: `GET /api/v1/leave/stats/by-status`
3. Department report: `GET /api/v1/leave/stats/department/{id}`

---

## 📌 Implementation Checklist

- [x] HR can create leave cycles
- [x] HR can create leave types with limits
- [x] HR can allocate leave balance to employees
- [x] HR can adjust carry forward
- [x] Employees can apply for leave
- [x] Employees can view leave requests
- [x] Employees can check balance
- [x] Employees can cancel pending leaves
- [x] Managers can view pending leaves
- [x] Managers can approve/reject leaves
- [x] Admin can view employee details
- [x] Admin can view statistics
- [x] Overlap validation
- [x] Balance validation
- [ ] Authentication & Authorization (TODO)
- [ ] Email notifications (TODO)
- [ ] Leave audit logs (TODO)
- [ ] Bulk operations (TODO)

---

## 🔄 Next Steps

1. **Add Authentication**: Implement JWT/Session-based auth
2. **Add Authorization**: Map endpoints to roles (HR, Manager, Employee, Admin)
3. **Email Notifications**: Send emails on leave approval/rejection
4. **Audit Logs**: Track all leave action history
5. **Bulk Operations**: Allocate leaves to multiple employees
6. **Public Holidays**: Integration with holiday calendar
7. **Attendance Integration**: Auto-mark attendance for approved leaves
