# Employee Deletion Guide

## Overview

You can now delete employees from the database in two ways:

1. **Soft Delete** (default) - Mark as deleted, keep in database
2. **Hard Delete** - Permanently remove from database

## Setup

Run the database migration to update foreign key constraints:

```bash
alembic upgrade head
```

Then restart the API:

```bash
Ctrl+C
uvicorn app.main:app --reload
```

## API Endpoint

### Delete Employee

```
DELETE /employees/{employee_id}
```

**Query Parameters:**

- `hard_delete=false` (default) - Soft delete
- `hard_delete=true` - Hard delete

## Soft Delete (Default)

Marks the employee as deleted but keeps their record in the database for auditing.

```bash
# Delete employee ID 5 (soft delete - default)
curl -X DELETE http://localhost:8000/employees/5

# Same as above (explicit)
curl -X DELETE "http://localhost:8000/employees/5?hard_delete=false"
```

**What happens:**

- Sets `is_deleted = true`
- Employee still in database
- Won't appear in GET requests
- Can recover if needed
- Attendance records remain linked

## Hard Delete

Permanently removes the employee from the database.

```bash
# Permanently delete employee ID 5
curl -X DELETE "http://localhost:8000/employees/5?hard_delete=true"
```

**What happens:**

- Employee completely removed from database
- Cannot be recovered
- Related foreign keys set to NULL:
  - role_id → NULL
  - department_id → NULL
  - shift_id → NULL
  - manager_id → NULL (for team members)
- Attendance records keep employee_id reference (nullable)
- Raw attendance records keep employee_id reference (nullable)

## Comparison

| Feature         | Soft Delete                  | Hard Delete               |
| --------------- | ---------------------------- | ------------------------- |
| Database Impact | Marks `is_deleted=true`      | Removes record completely |
| Recoverability  | Can query `is_deleted=false` | Cannot recover            |
| Related Records | Preserved, still linked      | FK set to NULL            |
| Attendance      | Remains linked               | Remains linked (orphaned) |
| Use Case        | Temporary/audit needs        | Final archival            |

## Examples

### Soft Delete (Keep for audit)

```bash
curl -X DELETE http://localhost:8000/employees/5
```

- Employee marked as deleted
- Can be recovered later if needed
- Audit trail preserved

### Hard Delete (Permanent removal)

```bash
curl -X DELETE "http://localhost:8000/employees/5?hard_delete=true"
```

- Employee completely removed
- Cannot be recovered
- Manager assignments cleared for team members
- Department/role assignments cleared

## Database Changes

The Employee model now has:

```python
role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
```

This means:

- Employees can be deleted without foreign key violations
- Related references are set to NULL automatically
- Much more flexible than the previous RESTRICT constraints

## Testing

### Check if employee exists

```bash
curl http://localhost:8000/employees/5
```

### Soft delete

```bash
curl -X DELETE http://localhost:8000/employees/5
```

### Try retrieving deleted employee

```bash
curl http://localhost:8000/employees/5
# Returns: 404 Not Found
```

### Hard delete (permanent)

```bash
curl -X DELETE "http://localhost:8000/employees/5?hard_delete=true"
```

### Verify deletion from database

```sql
SELECT * FROM employees WHERE id = 5;
-- No result for hard delete
-- `is_deleted = true` for soft delete
```

## SQL Queries

### Find soft-deleted employees

```sql
SELECT id, f_name, l_name, is_deleted FROM employees WHERE is_deleted = true;
```

### Restore soft-deleted employee (if needed)

```sql
UPDATE employees SET is_deleted = false WHERE id = 5;
```

### Check if hard deleted

```sql
SELECT COUNT(*) FROM employees WHERE id = 5;
-- Result: 0 (permanently deleted)
```

## Cascading Effects

When you hard delete an employee:

1. **Manager assignments** - Team members' `manager_id` becomes NULL
2. **Department/Role/Shift** - FK fields become NULL
3. **Attendance records** - `employee_id` remains (if nullable), orphaned but preserved
4. **Raw attendance records** - `employee_id` remains (nullable), orphaned but preserved
5. **Login account** - Depends on FK cascade rules (check LoginAccount model)

## Recommended Workflow

### For Temporary Cases (Contractors, Interns)

```bash
# Soft delete first
curl -X DELETE http://localhost:8000/employees/5
# If you need to restore
UPDATE employees SET is_deleted = false WHERE id = 5;
```

### For Permanent Removal (Resigned, Retired)

```bash
# Ensure no dependencies
curl http://localhost:8000/employees/5
# Hard delete
curl -X DELETE "http://localhost:8000/employees/5?hard_delete=true"
```

### Bulk Operations (SQL)

```sql
-- Soft delete employees by department
UPDATE employees SET is_deleted = true
WHERE department_id = 10 AND employment_status = 'terminated';

-- Hard delete old contractors
DELETE FROM employees
WHERE employment_status = 'inactive'
AND is_deleted = true
AND created_at < DATE_SUB(NOW(), INTERVAL 1 YEAR);
```

## Safety Checks Before Deletion

Before hard deleting, verify:

1. All related projects/tasks are reassigned
2. Attendance data is backed up if needed
3. Manager assignments are updated
4. No active login sessions

## Error Handling

### 404 Not Found

```json
{ "detail": "Employee not found" }
```

Either employee doesn't exist or is already soft deleted.

### 204 No Content

Successful deletion (whether soft or hard).

## Troubleshooting

### Can't Delete: "Foreign Key Constraint Failed"

- Ensure migration was run: `alembic upgrade head`
- Restart API server
- Check for LoginAccount dependencies

### Employee Still Visible After Soft Delete

- This is expected - use `?linked=false` filter when querying
- Soft deleted employees have `is_deleted = true`

### Hard Delete Fails

- Check attendance/raw_attendance references
- Those tables have nullable employee_id (should be fine)
- Check LoginAccount model constraints

## Next Steps

1. ✓ Run migration: `alembic upgrade head`
2. ✓ Restart API: `uvicorn app.main:app --reload`
3. ✓ Test soft delete: `DELETE /employees/{id}`
4. ✓ Test hard delete: `DELETE /employees/{id}?hard_delete=true`
5. ✓ Verify in database: `SELECT * FROM employees WHERE id = {id}`
