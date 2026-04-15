from datetime import date, datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user

from app.models.leaves import (
    LeaveType,
    LeaveBalance,
    LeaveRequest,
    LeaveCycle,
    LeaveStatusEnum,
)

from app.schemas.leave import (
    LeaveRequestCreate,
    LeaveRequestOut,
    LeaveAction,
    LeaveBalanceOut,
    LeaveCycleCreate,
    LeaveCycleOut,
    LeaveTypeCreate,
    LeaveTypeOut,
)

from app.crud import leave as leave_crud

router = APIRouter()


# =========================================================
# 🔹 HR ENDPOINTS: LEAVE CYCLES
# =========================================================

@router.post("/cycles", response_model=LeaveCycleOut, tags=["HR - Leave Cycles"])
def create_leave_cycle_api(
    payload: LeaveCycleCreate,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user),  # 🔥 Add auth & HR check
):
    """Create a new leave cycle (HR only)"""
    try:
        cycle = leave_crud.create_leave_cycle(
            db,
            name=payload.name,
            start_month=payload.start_month,
            start_day=payload.start_day,
            end_month=payload.end_month,
            end_day=payload.end_day,
        )
        return cycle
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cycles", response_model=List[LeaveCycleOut], tags=["HR - Leave Cycles"])
def get_all_leave_cycles_api(db: Session = Depends(get_db)):
    """Get all leave cycles"""
    cycles = leave_crud.get_all_leave_cycles(db)
    return cycles


@router.get("/cycles/{cycle_id}", response_model=LeaveCycleOut, tags=["HR - Leave Cycles"])
def get_leave_cycle_api(cycle_id: int, db: Session = Depends(get_db)):
    """Get a specific leave cycle"""
    cycle = leave_crud.get_leave_cycle(db, cycle_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="Leave cycle not found")
    return cycle


@router.put("/cycles/{cycle_id}", response_model=LeaveCycleOut, tags=["HR - Leave Cycles"])
def update_leave_cycle_api(
    cycle_id: int,
    payload: LeaveCycleCreate,
    db: Session = Depends(get_db),
):
    """Update leave cycle details (HR only)"""
    try:
        cycle = leave_crud.update_leave_cycle(
            db,
            cycle_id,
            name=payload.name,
            start_month=payload.start_month,
            start_day=payload.start_day,
            end_month=payload.end_month,
            end_day=payload.end_day,
        )
        return cycle
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cycles/{cycle_id}/deactivate", response_model=LeaveCycleOut, tags=["HR - Leave Cycles"])
def deactivate_leave_cycle_api(
    cycle_id: int,
    db: Session = Depends(get_db),
):
    """Deactivate a leave cycle"""
    try:
        cycle = leave_crud.deactivate_leave_cycle(db, cycle_id)
        return cycle
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# 🔹 HR ENDPOINTS: LEAVE TYPES
# =========================================================

@router.post("/types", response_model=LeaveTypeOut, tags=["HR - Leave Types"])
def create_leave_type_api(
    payload: LeaveTypeCreate,
    db: Session = Depends(get_db),
):
    """Create a new leave type with limits (HR only)"""
    try:
        # Validate cycle exists
        cycle = leave_crud.get_leave_cycle(db, payload.leave_cycle_id)
        if not cycle:
            raise HTTPException(status_code=404, detail="Leave cycle not found")
        
        leave_type = leave_crud.create_leave_type(
            db,
            name=payload.name,
            is_paid=payload.is_paid,
            max_per_cycle=payload.max_per_cycle,
            carry_forward=payload.carry_forward,
            max_carry_forward=payload.max_carry_forward,
            leave_cycle_id=payload.leave_cycle_id,
        )
        return leave_type
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/types", response_model=List[LeaveTypeOut], tags=["HR - Leave Types"])
def get_all_leave_types_api(db: Session = Depends(get_db)):
    """Get all leave types"""
    types = leave_crud.get_all_leave_types(db)
    return types


@router.get("/types/{leave_type_id}", response_model=LeaveTypeOut, tags=["HR - Leave Types"])
def get_leave_type_api(leave_type_id: int, db: Session = Depends(get_db)):
    """Get a specific leave type"""
    leave_type = leave_crud.get_leave_type(db, leave_type_id)
    if not leave_type:
        raise HTTPException(status_code=404, detail="Leave type not found")
    return leave_type


@router.put("/types/{leave_type_id}", response_model=LeaveTypeOut, tags=["HR - Leave Types"])
def update_leave_type_api(
    leave_type_id: int,
    payload: LeaveTypeCreate,
    db: Session = Depends(get_db),
):
    """Update leave type limits (HR only)"""
    try:
        leave_type = leave_crud.update_leave_type(
            db,
            leave_type_id,
            name=payload.name,
            is_paid=payload.is_paid,
            max_per_cycle=payload.max_per_cycle,
            carry_forward=payload.carry_forward,
            max_carry_forward=payload.max_carry_forward,
        )
        return leave_type
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cycles/{cycle_id}/types", response_model=List[LeaveTypeOut], tags=["HR - Leave Types"])
def get_leave_types_by_cycle_api(cycle_id: int, db: Session = Depends(get_db)):
    """Get all leave types in a specific cycle"""
    types = leave_crud.get_leave_types_by_cycle(db, cycle_id)
    return types


@router.delete("/types/{leave_type_id}", tags=["HR - Leave Types"])
def delete_leave_type_api(leave_type_id: int, db: Session = Depends(get_db)):
    """Delete a leave type (HR only)"""
    try:
        result = leave_crud.delete_leave_type(db, leave_type_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# 🔹 HR ENDPOINTS: LEAVE BALANCE ALLOCATION
# =========================================================

class AllocateLeavePayload:
    employee_id: int
    leave_type_id: int
    allocated_days: float
    cycle_start_date: date
    cycle_end_date: date

@router.post("/allocate", response_model=LeaveBalanceOut, tags=["HR - Leave Balance"])
def allocate_leave_balance_api(
    employee_id: int = Query(...),
    leave_type_id: int = Query(...),
    allocated_days: float = Query(...),
    cycle_start_date: date = Query(...),
    cycle_end_date: date = Query(...),
    db: Session = Depends(get_db),
):
    """Allocate leave balance to an employee (HR only)"""
    try:
        # Validate leave type exists
        leave_type = leave_crud.get_leave_type(db, leave_type_id)
        if not leave_type:
            raise HTTPException(status_code=404, detail="Leave type not found")
        
        balance = leave_crud.allocate_leave_balance(
            db,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            leave_cycle_id=leave_type.leave_cycle_id,
            allocated_days=allocated_days,
            cycle_start_date=cycle_start_date,
            cycle_end_date=cycle_end_date,
        )
        return balance
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/adjust-carry-forward", response_model=LeaveBalanceOut, tags=["HR - Leave Balance"])
def adjust_carry_forward_api(
    employee_id: int = Query(...),
    leave_type_id: int = Query(...),
    cycle_start_date: date = Query(...),
    carry_forward_days: float = Query(...),
    db: Session = Depends(get_db),
):
    """Adjust carry forward leaves from previous cycle (HR only)"""
    try:
        balance = leave_crud.adjust_carry_forward(
            db,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            cycle_start_date=cycle_start_date,
            carry_forward_days=carry_forward_days,
        )
        return balance
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# 🔹 EMPLOYEE ENDPOINTS: APPLY & VIEW LEAVES
# =========================================================

@router.post("/apply", response_model=LeaveRequestOut, tags=["Employee - Leaves"])
def apply_leave_api(
    payload: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_employee: "Employee" = Depends(get_current_user),
):
    """Employee applies for leave"""
    try:
        employee_id = current_employee.id
        leave_type = db.query(LeaveType).get(payload.leave_type_id)
        if not leave_type:
            raise HTTPException(status_code=404, detail="Leave type not found")

        leave_crud.validate_no_overlap(db, employee_id, payload.start_date, payload.end_date)

        balance = leave_crud.get_or_create_balance(db, employee_id, leave_type, date.today())

        days = leave_crud.calculate_days(payload.start_date, payload.end_date, payload.is_half_day)

        if balance.remaining < days:
            raise HTTPException(status_code=400, detail=f"Insufficient leave balance. Available: {balance.remaining}, Requested: {days}")

        leave = LeaveRequest(
            employee_id=employee_id,
            leave_type_id=payload.leave_type_id,
            leave_cycle_id=leave_type.leave_cycle_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            days=days,
            is_half_day=payload.is_half_day,
            reason=payload.reason,
            status=LeaveStatusEnum.pending,
        )

        db.add(leave)
        balance.pending += days

        db.commit()
        db.refresh(leave)

        return leave
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my", response_model=List[LeaveRequestOut], tags=["Employee - Leaves"])
def get_my_leaves(
    db: Session = Depends(get_db),
    current_employee: "Employee" = Depends(get_current_user),
    status: str = Query(None),
):
    """Employee views their leave requests"""
    query = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == current_employee.id
    )
    
    if status:
        query = query.filter(LeaveRequest.status == status)
    
    return query.order_by(LeaveRequest.created_at.desc()).all()


@router.get("/balance", response_model=List[LeaveBalanceOut], tags=["Employee - Leaves"])
def get_my_balance(
    db: Session = Depends(get_db),
    current_employee: "Employee" = Depends(get_current_user),
):
    """Employee views their leave balance"""
    return db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == current_employee.id
    ).all()


@router.get("/balance/{leave_type_id}", response_model=LeaveBalanceOut, tags=["Employee - Leaves"])
def get_my_balance_for_type(
    leave_type_id: int,
    db: Session = Depends(get_db),
    current_employee: "Employee" = Depends(get_current_user),
):
    """Employee views balance for a specific leave type"""
    try:
        balance = leave_crud.get_employee_balance_for_leave_type(
            db,
            employee_id=current_employee.id,
            leave_type_id=leave_type_id,
        )
        if not balance:
            raise HTTPException(status_code=404, detail="Leave balance not found")
        return balance
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{leave_id}/cancel", response_model=LeaveRequestOut, tags=["Employee - Leaves"])
def cancel_leave_api(
    leave_id: int,
    db: Session = Depends(get_db),
    employee_id: int = 1,
):
    """Employee cancels their leave request"""
    try:
        leave = leave_crud.cancel_leave(db, leave_id, employee_id)
        return leave
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# 🔹 MANAGER ENDPOINTS: APPROVE / REJECT LEAVES
# =========================================================

@router.post("/{leave_id}/action", response_model=LeaveRequestOut, tags=["Manager - Approvals"])
def leave_action_api(
    leave_id: int,
    payload: LeaveAction,
    db: Session = Depends(get_db),
    approver_id: int = 1,  # 🔥 replace with auth
):
    """Manager approves or rejects leave request"""
    try:
        leave = leave_crud.process_leave_action(
            db,
            leave_id=leave_id,
            action=payload.action,
            approver_id=approver_id,
        )
        return leave
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pending", response_model=List[LeaveRequestOut], tags=["Manager - Approvals"])
def get_pending_leaves_api(db: Session = Depends(get_db)):
    """Get all pending leave requests for approval"""
    leaves = db.query(LeaveRequest).filter(
        LeaveRequest.status == LeaveStatusEnum.pending
    ).order_by(LeaveRequest.created_at).all()
    return leaves


# =========================================================
# 🔹 ADMIN ENDPOINTS: EMPLOYEE DATA
# =========================================================

@router.get("/employee/{employee_id}", response_model=List[LeaveRequestOut], tags=["Admin - Employees"])
def get_employee_leaves(
    employee_id: int,
    db: Session = Depends(get_db),
    status: str = Query(None),
):
    """Admin views all leaves of an employee"""
    query = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id
    )
    
    if status:
        query = query.filter(LeaveRequest.status == status)
    
    return query.all()


@router.get("/employee/{employee_id}/balance", response_model=List[LeaveBalanceOut], tags=["Admin - Employees"])
def get_employee_balance(
    employee_id: int,
    db: Session = Depends(get_db),
):
    """Admin views leave balance of an employee"""
    return db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == employee_id
    ).all()


@router.get("/employee/{employee_id}/summary", tags=["Admin - Employees"])
def get_employee_leave_summary(
    employee_id: int,
    db: Session = Depends(get_db),
):
    """Admin views leave summary for an employee"""
    balances = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == employee_id
    ).all()
    
    summary = []
    for balance in balances:
        summary.append({
            "leave_type": balance.leave_type.name,
            "allocated": balance.allocated,
            "used": balance.used,
            "pending": balance.pending,
            "carry_forward": balance.carry_forward,
            "remaining": balance.remaining,
        })
    
    return summary


# =========================================================
# 🔹 ANALYTICS & REPORTING
# =========================================================

@router.get("/stats/by-status", tags=["Reports"])
def get_leaves_by_status(
    db: Session = Depends(get_db),
    status: str = Query(None),
):
    """Get leave statistics grouped by status"""
    if status:
        leaves = leave_crud.get_leaves_by_status(db, status)
        return {"status": status, "count": len(leaves)}
    
    result = {}
    for s in [LeaveStatusEnum.pending, LeaveStatusEnum.approved, LeaveStatusEnum.rejected, LeaveStatusEnum.cancelled]:
        count = db.query(LeaveRequest).filter(LeaveRequest.status == s).count()
        result[s.value] = count
    
    return result


@router.get("/stats/department/{department_id}", tags=["Reports"])
def get_leaves_by_department(department_id: int, db: Session = Depends(get_db)):
    """Get leave statistics for a department"""
    from app.models.employee import Employee
    
    employees = db.query(Employee).filter(Employee.department_id == department_id).all()
    employee_ids = [e.id for e in employees]
    
    leaves = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id.in_(employee_ids)
    ).all()
    
    return {
        "department_id": department_id,
        "total_employees": len(employees),
        "total_leaves": len(leaves),
        "pending": len([l for l in leaves if l.status == LeaveStatusEnum.pending]),
        "approved": len([l for l in leaves if l.status == LeaveStatusEnum.approved]),
        "rejected": len([l for l in leaves if l.status == LeaveStatusEnum.rejected]),
    }