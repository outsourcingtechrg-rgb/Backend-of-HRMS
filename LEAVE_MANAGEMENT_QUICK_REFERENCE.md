# Leave Management - Quick Reference Guide

## File Structure

```
app/
├── models/
│   ├── LeaveTypes.py          # Leave type definitions
│   ├── LeaveAllocation.py      # Employee leave allocations
│   ├── LeaveRequest.py         # Leave request submissions
│   └── LeaveTransaction.py     # Audit trail
├── schemas/
│   └── leave.py                # All Pydantic models
├── crud/
│   └── leave.py                # Business logic (CRUD operations)
└── api/
    └── v1/
        └── leave.py            # API endpoints
```

## Core CRUD Functions

### LeaveType Functions

- `create_leave_type(db, leave_type_in)` → LeaveType
- `get_leave_type(db, leave_type_id)` → LeaveType | None
- `get_leave_type_by_name(db, name)` → LeaveType | None
- `get_all_leave_types(db, skip, limit, is_active)` → List[LeaveType]
- `update_leave_type(db, leave_type, leave_type_in)` → LeaveType
- `delete_leave_type(db, leave_type)` → None

### LeaveAllocation Functions

- `create_leave_allocation(db, allocation_in)` → LeaveAllocation
- `get_leave_allocation(db, allocation_id)` → LeaveAllocation | None
- `get_leave_allocation_by_employee_and_type(db, employee_id, leave_type_id, year)` → LeaveAllocation | None
- `get_employee_leave_allocations(db, employee_id, year, skip, limit)` → List[LeaveAllocation]
- `update_leave_allocation(db, allocation, allocation_in)` → LeaveAllocation
- `delete_leave_allocation(db, allocation)` → None
- **`get_available_leave_balance(db, employee_id, leave_type_id, year)` → float** ⭐ Key function
- `update_allocation_on_approval(db, employee_id, leave_type_id, year, days)` → LeaveAllocation
- `revert_allocation_on_rejection(db, employee_id, leave_type_id, year, days)` → LeaveAllocation

### LeaveRequest Functions

- `create_leave_request(db, request_in)` → LeaveRequest
  - ✅ Validates balance automatically
  - ✅ Raises HTTPException if insufficient balance
- `get_leave_request(db, request_id)` → LeaveRequest | None
- `get_employee_leave_requests(db, employee_id, status, skip, limit)` → List[LeaveRequest]
- `get_pending_leave_requests(db, skip, limit)` → List[LeaveRequest]
- `update_leave_request(db, leave_request, request_in)` → LeaveRequest
- **`approve_leave_request(db, leave_request, approver_id)` → LeaveRequest** ⭐
  - Updates allocation (used_days += days)
  - Creates deduction transaction
  - Sets status to "approved"
- **`reject_leave_request(db, leave_request, approver_id)` → LeaveRequest** ⭐
  - No allocation changes
  - Sets status to "rejected"
- **`cancel_leave_request(db, leave_request, canceller_id)` → LeaveRequest** ⭐
  - Reverts allocation (used_days -= days)
  - Creates reversal transaction
  - Sets status to "cancelled"
- `delete_leave_request(db, leave_request)` → None

### LeaveTransaction Functions

- `create_leave_transaction(db, transaction_in)` → LeaveTransaction
- `get_leave_transaction(db, transaction_id)` → LeaveTransaction | None
- `get_employee_leave_transactions(db, employee_id, transaction_type, skip, limit)` → List[LeaveTransaction]
- `get_leave_type_transactions(db, leave_type_id, skip, limit)` → List[LeaveTransaction]

---

## API Endpoints Quick Look

### Leave Types

| Method | Endpoint             | Purpose               |
| ------ | -------------------- | --------------------- |
| POST   | `/leaves/types`      | Create leave type     |
| GET    | `/leaves/types`      | List leave types      |
| GET    | `/leaves/types/{id}` | Get single leave type |
| PUT    | `/leaves/types/{id}` | Update leave type     |
| DELETE | `/leaves/types/{id}` | Delete leave type     |

### Leave Allocations

| Method | Endpoint                             | Purpose                  |
| ------ | ------------------------------------ | ------------------------ |
| POST   | `/leaves/allocations`                | Create allocation        |
| GET    | `/leaves/allocations/{id}`           | Get allocation           |
| GET    | `/leaves/employees/{id}/allocations` | Get employee allocations |
| GET    | `/leaves/employees/{id}/balance`     | Get balance summary ⭐   |
| PUT    | `/leaves/allocations/{id}`           | Update allocation        |
| DELETE | `/leaves/allocations/{id}`           | Delete allocation        |

### Leave Requests

| Method | Endpoint                          | Purpose                       |
| ------ | --------------------------------- | ----------------------------- |
| POST   | `/leaves/requests`                | Submit request                |
| GET    | `/leaves/requests`                | List pending requests         |
| GET    | `/leaves/requests/{id}`           | Get single request            |
| GET    | `/leaves/employees/{id}/requests` | Get employee requests         |
| PUT    | `/leaves/requests/{id}`           | Update request (pending only) |
| POST   | `/leaves/requests/{id}/approve`   | Approve ⭐                    |
| POST   | `/leaves/requests/{id}/reject`    | Reject ⭐                     |
| POST   | `/leaves/requests/{id}/cancel`    | Cancel ⭐                     |
| DELETE | `/leaves/requests/{id}`           | Delete (pending only)         |

### Leave Transactions

| Method | Endpoint                              | Purpose                             |
| ------ | ------------------------------------- | ----------------------------------- |
| GET    | `/leaves/transactions/{id}`           | Get transaction                     |
| GET    | `/leaves/employees/{id}/transactions` | Get employee transactions           |
| GET    | `/leaves/transactions`                | List transactions (filter required) |
| POST   | `/leaves/transactions`                | Create manual transaction           |

---

## Key Workflows

### Workflow 1: Employee Requests Leave

```
1. Employee submits leave request (POST /leaves/requests)
   ↓
2. System validates:
   - Leave allocation exists ✓
   - Balance available ✓
   - Dates valid ✓
   ↓
3. Request created with status="pending"
   ↓
4. Manager views in pending requests (GET /leaves/requests)
```

### Workflow 2: Manager Approves Leave

```
1. Manager calls approve (POST /leaves/requests/{id}/approve)
   ↓
2. System:
   - Updates allocation.used_days += days
   - Creates transaction (type="deduction")
   - Sets status="approved"
   ↓
3. Employee's available balance reduced
```

### Workflow 3: Cancel Approved Leave

```
1. Employee/HR calls cancel (POST /leaves/requests/{id}/cancel)
   ↓
2. System:
   - Updates allocation.used_days -= days
   - Creates transaction (type="reversal")
   - Sets status="cancelled"
   ↓
3. Employee's available balance restored
```

### Workflow 4: Check Balance

```
1. GET /leaves/employees/{id}/balance?year=2024
   ↓
2. Returns:
   - allocated_days: 20
   - used_days: 3
   - carried_forward: 2
   - available_days: 19  (automatic calculation)
```

---

## Common Query Patterns

### Get All Leave Info for Employee

```python
# Get allocations
allocations = leave_crud.get_employee_leave_allocations(db, employee_id)

# Check balance for specific leave type
balance = leave_crud.get_available_leave_balance(
    db, employee_id, leave_type_id, 2024
)

# Get all requests
requests = leave_crud.get_employee_leave_requests(db, employee_id)

# Get all transactions
transactions = leave_crud.get_employee_leave_transactions(db, employee_id)
```

### Get Pending Approvals

```python
pending = leave_crud.get_pending_leave_requests(db, skip=0, limit=100)

for request in pending:
    print(f"Employee {request.employee_id}: {request.days} days - {request.reason}")
```

### Check if Employee Has Sufficient Leave

```python
available = leave_crud.get_available_leave_balance(
    db, employee_id, leave_type_id, 2024
)

if available >= requested_days:
    # Proceed with request
    pass
else:
    # Show error
    raise HTTPException(status_code=400, detail="Insufficient balance")
```

---

## Status Transitions Diagram

```
         create
request -------→ pending --------→ approved --------→ cancelled
                    ↓                 ↓
                 rejected             └─────→ can revert to pending
                                              (via cancel)

delete: only from pending
update: only in pending
```

---

## Transaction Types

| Type            | When               | Details                    |
| --------------- | ------------------ | -------------------------- |
| `allocation`    | Leave cycle begins | Initial allocation         |
| `carry_forward` | Year end/start     | Carried from previous year |
| `deduction`     | Leave approved     | Days deducted on approval  |
| `reversal`      | Leave cancelled    | Reversal of deduction      |
| `adjustment`    | HR manual entry    | HR adjustments             |

---

## Storage of Key Data

### In LeaveAllocation

- `allocated_days`: Total days allocated for year
- `used_days`: Days used (deducted on approval)
- `carried_forward`: Days carried from previous year
- **available = allocated + carried_forward - used**

### In LeaveRequest

- `status`: pending | approved | rejected | cancelled
- `action_by`: ID of approver (manager/HR)
- Dates: start_date, end_date, days

### In LeaveTransaction

- Complete audit trail
- Type indicates nature of change
- Created automatically on approval/rejection/cancellation

---

## Error Handling Examples

```python
# Example 1: Employee submits request with insufficient balance
try:
    request = leave_crud.create_leave_request(db, request_in)
except HTTPException as e:
    # e.detail = "Insufficient leave balance. Available: 5, Requested: 10"

# Example 2: Try to approve non-pending request
try:
    leave_crud.approve_leave_request(db, leave_request, approver_id)
except HTTPException as e:
    # e.detail = "Only pending leave requests can be approved"

# Example 3: Allocation already exists
try:
    leave_crud.create_leave_allocation(db, allocation_in)
except HTTPException as e:
    # e.detail = "Leave allocation already exists"
```

---

## Testing Checklist

- [ ] Create leave types
- [ ] Create allocations for employees
- [ ] Submit leave request (should validate balance)
- [ ] Try request with insufficient balance (should fail)
- [ ] Approve request (should update allocation)
- [ ] Check balance (should show reduced available days)
- [ ] View transactions (should show deduction)
- [ ] Cancel request (should restore balance)
- [ ] View transactions (should show deduction + reversal)
- [ ] Reject request (should not affect allocation)
- [ ] Try updating non-pending request (should fail)

---

## Integration Points

### With Employee Module

```python
from app.crud.employee import get_employee
employee = get_employee(db, employee_id)
```

### With HR System

- Use leave balance for payroll calculations
- Send notifications on status changes
- Generate leave reports

---

## Performance Notes

### Indexes

- LeaveAllocation: (employee_id, leave_type_id, year) - Unique
- LeaveRequest: (employee_id, status)
- LeaveTransaction: (employee_id)

### Query Optimization

- Use `get_employee_leave_allocations()` with year filter when possible
- Transactions are sorted by created_at DESC for audit trail
- Balance calculation is O(1) - just arithmetic

---

## Configuration

No special configuration needed. All leave types and allocations are managed via API. Database tables are auto-created from SQLAlchemy models.

---

## Related Files

- `/LEAVE_MANAGEMENT_COMPLETE.md` - Full documentation
- `app/models/LeaveTypes.py` - LeaveType model
- `app/models/LeaveAllocation.py` - LeaveAllocation model
- `app/models/LeaveRequest.py` - LeaveRequest model
- `app/models/LeaveTransaction.py` - LeaveTransaction model
- `app/schemas/leave.py` - All schemas
- `app/crud/leave.py` - All business logic
- `app/api/v1/leave.py` - All endpoints
- `app/api/router.py` - Where leave routes are registered

---

## Summary

✅ **Complete leave management system** with:

- Leave type configuration
- Allocation tracking with balance calculation
- Full request workflow (submit → approve/reject → optionally cancel)
- Automatic transaction logging
- Validation and error handling
- Comprehensive API endpoints

Ready for production use!
