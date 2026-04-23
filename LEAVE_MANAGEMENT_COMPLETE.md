# Leave Management Module - Complete Documentation

## Overview

The Leave Management Module provides a comprehensive system for managing employee leave requests, leave types, allocations, and transactions in the HRMS system.

## Architecture

### Components

#### 1. **Models** (`app/models/`)

- **LeaveType**: Defines different types of leave (Casual, Sick, Annual, etc.)
- **LeaveAllocation**: Tracks allocated leave days per employee per year
- **LeaveRequest**: Manages leave request submissions and approvals
- **LeaveTransaction**: Audit trail of all leave deductions and adjustments

#### 2. **Schemas** (`app/schemas/leave.py`)

Pydantic models for request/response validation with complete type safety.

#### 3. **CRUD Operations** (`app/crud/leave.py`)

Business logic layer handling:

- Leave type management
- Allocation management with balance calculations
- Leave request workflow (creation, approval, rejection, cancellation)
- Transaction logging

#### 4. **API Endpoints** (`app/api/v1/leave.py`)

RESTful endpoints organized by resource type with proper HTTP status codes.

---

## Module Features

### 1. **Leave Type Management**

Create and manage different leave types with configurable rules.

**Key Features:**

- Gender-specific leave (e.g., Maternity, Paternity)
- Carry forward option with limits
- Required documentation (e.g., medical certificate for sick leave)
- Min/Max days per request
- Paid vs unpaid leaves
- Reset months for annual cycles

### 2. **Leave Allocation**

Allocate leave days to employees per year with tracking.

**Key Features:**

- Per-employee, per-type, per-year allocation
- Track allocated, used, and carried-forward days
- Calculate available balance automatically
- Enforce unique constraints (no duplicates)

### 3. **Leave Request Workflow**

Complete workflow for requesting and approving leave.

**Key Features:**

- Automatic balance validation before submission
- Multi-status workflow: pending → approved/rejected
- Cancellation of approved leaves
- Soft rules for allowed negative balances
- Request history and audit trail

### 4. **Leave Transactions**

Complete audit trail of all leave movements.

**Transaction Types:**

- `allocation`: Initial leave allocation
- `carry_forward`: Leave carried from previous year
- `deduction`: Leave deducted from approval
- `reversal`: Deduction reversed (e.g., cancellation)
- `adjustment`: Manual adjustments by HR

---

## API Endpoints

### Leave Type Endpoints

#### Create Leave Type

```http
POST /leaves/types
Content-Type: application/json

{
  "name": "Casual Leave",
  "code": "CL",
  "description": "Casual leave for employees",
  "days_per_year": 12,
  "carry_forward": true,
  "max_carry_forward": 5,
  "is_active": true,
  "is_paid": true,
  "reset_month": 1
}
```

#### List Leave Types

```http
GET /leaves/types?is_active=true&skip=0&limit=100
```

#### Get Leave Type

```http
GET /leaves/types/{leave_type_id}
```

#### Update Leave Type

```http
PUT /leaves/types/{leave_type_id}
Content-Type: application/json

{
  "max_carry_forward": 10
}
```

#### Delete Leave Type

```http
DELETE /leaves/types/{leave_type_id}
```

---

### Leave Allocation Endpoints

#### Create Allocation

```http
POST /leaves/allocations
Content-Type: application/json

{
  "employee_id": 1,
  "leave_type_id": 1,
  "year": 2024,
  "allocated_days": 12,
  "used_days": 0,
  "carried_forward": 0
}
```

#### Get Employee Allocations

```http
GET /leaves/employees/{employee_id}/allocations?year=2024&skip=0&limit=100
```

#### Get Employee Leave Balance

```http
GET /leaves/employees/{employee_id}/balance?year=2024
```

**Response Example:**

```json
{
  "employee_id": 1,
  "year": 2024,
  "balances": [
    {
      "employee_id": 1,
      "year": 2024,
      "leave_type_id": 1,
      "leave_type_name": "Casual Leave",
      "allocated_days": 12,
      "used_days": 3,
      "carried_forward": 1,
      "available_days": 10
    }
  ]
}
```

#### Update Allocation

```http
PUT /leaves/allocations/{allocation_id}
Content-Type: application/json

{
  "allocated_days": 15,
  "used_days": 5
}
```

#### Delete Allocation

```http
DELETE /leaves/allocations/{allocation_id}
```

---

### Leave Request Endpoints

#### Submit Leave Request

```http
POST /leaves/requests
Content-Type: application/json

{
  "employee_id": 1,
  "leave_type_id": 1,
  "start_date": "2024-02-15",
  "end_date": "2024-02-17",
  "days": 3,
  "reason": "Personal reasons"
}
```

**Validation:**

- Checks available balance
- Employees cannot exceed days_per_year limit
- Start date must be before end date
- Days must match date range

#### Get Employee Requests

```http
GET /leaves/employees/{employee_id}/requests?status=pending&skip=0&limit=100
```

**Status Options:** `pending`, `approved`, `rejected`, `cancelled`

#### Get Single Request

```http
GET /leaves/requests/{request_id}
```

#### Update Request (Pending Only)

```http
PUT /leaves/requests/{request_id}
Content-Type: application/json

{
  "reason": "Updated reason"
}
```

#### Approve Request

```http
POST /leaves/requests/{request_id}/approve
Content-Type: application/json

{
  "action_by": 5
}
```

**Actions on Approval:**

1. Update leave allocation (increment used_days)
2. Create leave transaction (type: deduction)
3. Update request status to 'approved'

#### Reject Request

```http
POST /leaves/requests/{request_id}/reject
Content-Type: application/json

{
  "action_by": 5
}
```

**Actions on Rejection:**

1. Request status changed to 'rejected'
2. No changes to allocation

#### Cancel Request

```http
POST /leaves/requests/{request_id}/cancel?canceller_id=5
```

**Actions on Cancellation:**

1. Only approved requests can be cancelled
2. Revert leave allocation (decrement used_days)
3. Create reversal transaction
4. Update request status to 'cancelled'

#### Delete Request (Pending Only)

```http
DELETE /leaves/requests/{request_id}
```

---

### Leave Transaction Endpoints

#### Get Employee Transactions

```http
GET /leaves/employees/{employee_id}/transactions?transaction_type=deduction&skip=0&limit=100
```

#### Get Transactions by Type

```http
GET /leaves/transactions?employee_id=1&transaction_type=deduction
```

#### Get Single Transaction

```http
GET /leaves/transactions/{transaction_id}
```

#### Create Manual Transaction

```http
POST /leaves/transactions
Content-Type: application/json

{
  "employee_id": 1,
  "leave_type_id": 1,
  "days": 2,
  "type": "adjustment"
}
```

---

## Usage Examples

### Scenario 1: Annual Leave Setup

#### Step 1: Create Leave Types

```bash
curl -X POST http://localhost:8000/leaves/types \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Annual Leave",
    "code": "AL",
    "description": "Annual paid leave",
    "days_per_year": 20,
    "carry_forward": true,
    "max_carry_forward": 5,
    "reset_month": 1,
    "is_active": true,
    "is_paid": true
  }'
```

#### Step 2: Allocate Leaves to Employees

```bash
curl -X POST http://localhost:8000/leaves/allocations \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 1,
    "leave_type_id": 1,
    "year": 2024,
    "allocated_days": 20,
    "used_days": 0,
    "carried_forward": 2
  }'
```

#### Step 3: Check Balance

```bash
curl http://localhost:8000/leaves/employees/1/balance?year=2024
```

---

### Scenario 2: Leave Request Workflow

#### Step 1: Employee Submits Request

```bash
curl -X POST http://localhost:8000/leaves/requests \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 1,
    "leave_type_id": 1,
    "start_date": "2024-03-01",
    "end_date": "2024-03-05",
    "days": 5,
    "reason": "Annual vacation"
  }'
```

Response: `request_id: 10`

#### Step 2: Manager Approves

```bash
curl -X POST http://localhost:8000/leaves/requests/10/approve \
  -H "Content-Type: application/json" \
  -d '{
    "action_by": 5
  }'
```

#### Step 3: Verify Updated Balance

```bash
curl http://localhost:8000/leaves/employees/1/balance?year=2024
```

- available_days should be reduced by 5

#### Step 4: View Transactions

```bash
curl http://localhost:8000/leaves/employees/1/transactions?transaction_type=deduction
```

- Shows deduction transaction for 5 days

---

### Scenario 3: Cancel Approved Leave

```bash
# Cancel the approved leave
curl -X POST http://localhost:8000/leaves/requests/10/cancel?canceller_id=1

# Verify balance is restored
curl http://localhost:8000/leaves/employees/1/balance?year=2024

# View transactions
curl http://localhost:8000/leaves/employees/1/transactions
# Shows both deduction and reversal transactions
```

---

## Business Rules

### Validation Rules

1. **Balance Check**: Cannot request more days than available
2. **Date Validation**: start_date ≤ end_date
3. **Allocation Requirement**: Must have allocation for leave type
4. **Status Transitions**:
   - pending → approved or rejected
   - approved → cancelled
   - Only pending requests can be deleted

### Carry Forward Rules

1. Configurable per leave type
2. Maximum carry forward limit enforcement
3. Reset on annual cycle

### Gender-Specific Leave

- Can be restricted to specific gender
- Useful for maternity/paternity leave
- Optional field

---

## Database Schema Notes

### LeaveTypes Table

```sql
CREATE TABLE leave_types (
  id: Primary Key
  name: String (Unique)
  code: String (Unique, Optional)
  days_per_year: Float
  carry_forward: Boolean
  max_carry_forward: Float (Optional)
  gender_specific: String (Optional)
  reset_month: Integer (Optional)
  is_active: Boolean
  is_paid: Boolean
  requires_document: Boolean
  created_at: DateTime (Auto)
  updated_at: DateTime (Auto)
)
```

### LeaveAllocations Table

```sql
CREATE TABLE leave_allocations (
  id: Primary Key
  employee_id: Foreign Key -> employees
  leave_type_id: Foreign Key -> leave_types
  year: Integer (Indexed)
  allocated_days: Float
  used_days: Float
  carried_forward: Float
  created_at: DateTime

  Unique Constraint: (employee_id, leave_type_id, year)
)
```

### LeaveRequests Table

```sql
CREATE TABLE leave_requests (
  id: Primary Key
  employee_id: Foreign Key -> employees (Indexed)
  leave_type_id: Foreign Key -> leave_types
  start_date: Date
  end_date: Date
  days: Float
  reason: String (Optional)
  status: String (Indexed: pending, approved, rejected, cancelled)
  action_by: Foreign Key -> employees (Optional)
  created_at: DateTime
  updated_at: DateTime
)
```

### LeaveTransactions Table

```sql
CREATE TABLE leave_transactions (
  id: Primary Key
  employee_id: Foreign Key -> employees (Indexed)
  leave_type_id: Foreign Key -> leave_types
  leave_request_id: Foreign Key -> leave_requests (Optional)
  days: Float
  type: String (allocation, carry_forward, deduction, reversal, adjustment)
  created_at: DateTime
)
```

---

## Error Handling

### Common HTTP Status Codes

- **200 OK**: Successful GET request
- **201 Created**: Resource created successfully
- **204 No Content**: Successful deletion
- **400 Bad Request**: Validation failed (insufficient balance, invalid dates)
- **404 Not Found**: Resource not found
- **409 Conflict**: Duplicate entry (e.g., allocation already exists)

### Example Error Response

```json
{
  "detail": "Insufficient leave balance. Available: 5, Requested: 10"
}
```

---

## Integration with Other Modules

### Employee Module

- Leave requests are linked to employees
- Employee ID is required for all operations

### Attendance Module

- Can integrate to auto-mark absences during approved leave
- Leave days should reduce attendance counts

### Notifications

- Can trigger emails on:
  - Leave request submitted
  - Leave request approved
  - Leave request rejected
  - Leave expiry warnings

---

## Future Enhancements

1. **Leave Encashment**: Allow converting unused leave to salary
2. **Attendance Integration**: Auto-mark absences
3. **Email Notifications**: Automatic notifications on status changes
4. **Leave Calendar**: Visual calendar view
5. **Reports**:
   - Leave utilization reports
   - Department-wise leave statistics
   - Year-end leave expiry analysis
6. **Approvers Workflow**: Configure department-specific approvers
7. **Soft Lock**: Close leave allocation for previous years
8. **Leave Premium**: Different leave calculations based on tenure

---

## Testing Workflow

### Test Data Setup

```bash
# 1. Create leave types
curl -X POST http://localhost:8000/leaves/types -d "{leave type data}"

# 2. Create allocations for test employees
curl -X POST http://localhost:8000/leaves/allocations -d "{allocation data}"

# 3. Submit requests
curl -X POST http://localhost:8000/leaves/requests -d "{request data}"

# 4. Approve/reject/cancel
curl -X POST http://localhost:8000/leaves/requests/{id}/approve -d "{action data}"

# 5. Verify using balance and transaction endpoints
curl http://localhost:8000/leaves/employees/{id}/balance
curl http://localhost:8000/leaves/employees/{id}/transactions
```

---

## Configuration

No special configuration needed. The module uses:

- Database connection from `app.core.database`
- SQLAlchemy ORM for database operations
- Pydantic for validation
- FastAPI routers for endpoints

All leave types and allocations are dynamically configured through API.
