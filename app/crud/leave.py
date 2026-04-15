from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.leaves import (
    LeaveType,
    LeaveBalance,
    LeaveRequest,
    LeaveCycle,
    LeaveStatusEnum,
)
from app.models.employee import Employee


# =========================================================
# 🔹 HELPER: GET CURRENT CYCLE DATES
# =========================================================
def get_cycle_dates(leave_cycle: LeaveCycle, today: date):
    """
    Returns correct cycle start & end dates dynamically
    """

    year = today.year

    start_date = date(year, leave_cycle.start_month, leave_cycle.start_day)

    if today < start_date:
        start_date = date(year - 1, leave_cycle.start_month, leave_cycle.start_day)

    # calculate end date
    if leave_cycle.end_month >= leave_cycle.start_month:
        end_year = start_date.year
    else:
        end_year = start_date.year + 1

    end_date = date(end_year, leave_cycle.end_month, leave_cycle.end_day)

    return start_date, end_date


# =========================================================
# 🔹 HELPER: GET OR CREATE BALANCE
# =========================================================
def get_or_create_balance(
    db: Session,
    employee_id: int,
    leave_type: LeaveType,
    today: date,
):
    cycle = leave_type.leave_cycle

    start_date, end_date = get_cycle_dates(cycle, today)

    balance = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == employee_id,
        LeaveBalance.leave_type_id == leave_type.id,
        LeaveBalance.cycle_start_date == start_date,
    ).first()

    if balance:
        return balance

    # Create new balance
    balance = LeaveBalance(
        employee_id=employee_id,
        leave_type_id=leave_type.id,
        leave_cycle_id=cycle.id,
        cycle_start_date=start_date,
        cycle_end_date=end_date,
        allocated=leave_type.max_per_cycle,
        used=0,
        pending=0,
        carry_forward=0,
    )

    db.add(balance)
    db.flush()

    return balance


# =========================================================
# 🔹 HELPER: CALCULATE DAYS
# =========================================================
def calculate_days(start_date: date, end_date: date, is_half_day: bool):
    if is_half_day:
        return 0.5
    return (end_date - start_date).days + 1


# =========================================================
# 🔹 HELPER: CHECK OVERLAP
# =========================================================
def validate_no_overlap(db: Session, employee_id: int, start_date: date, end_date: date):
    overlap = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.status.in_(
            [LeaveStatusEnum.pending, LeaveStatusEnum.approved]
        ),
        LeaveRequest.start_date <= end_date,
        LeaveRequest.end_date >= start_date,
    ).first()

    if overlap:
        raise Exception("Leave already exists for selected dates")


# =========================================================
# 🔹 APPLY LEAVE
# =========================================================
def apply_leave(
    db: Session,
    employee_id: int,
    leave_type_id: int,
    start_date: date,
    end_date: date,
    reason: str = None,
    is_half_day: bool = False,
):
    leave_type = db.query(LeaveType).get(leave_type_id)
    if not leave_type:
        raise Exception("Invalid leave type")

    # validate overlap
    validate_no_overlap(db, employee_id, start_date, end_date)

    today = date.today()

    balance = get_or_create_balance(db, employee_id, leave_type, today)

    days = calculate_days(start_date, end_date, is_half_day)

    if balance.remaining < days:
        raise Exception("Insufficient leave balance")

    # create request
    leave = LeaveRequest(
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        leave_cycle_id=leave_type.leave_cycle_id,
        start_date=start_date,
        end_date=end_date,
        days=days,
        is_half_day=is_half_day,
        reason=reason,
        status=LeaveStatusEnum.pending,
    )

    db.add(leave)

    # update balance
    balance.pending += days

    db.commit()
    db.refresh(leave)

    return leave


# =========================================================
# 🔹 APPROVE / REJECT LEAVE
# =========================================================
def process_leave_action(
    db: Session,
    leave_id: int,
    action: str,
    approver_id: int,
):
    leave = db.query(LeaveRequest).get(leave_id)

    if not leave:
        raise Exception("Leave not found")

    if leave.status != LeaveStatusEnum.pending:
        raise Exception("Leave already processed")

    balance = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == leave.employee_id,
        LeaveBalance.leave_type_id == leave.leave_type_id,
        LeaveBalance.leave_cycle_id == leave.leave_cycle_id,
        LeaveBalance.cycle_start_date <= leave.start_date,
        LeaveBalance.cycle_end_date >= leave.end_date,
    ).first()

    if not balance:
        raise Exception("Balance not found")

    if action == "approve":
        leave.status = LeaveStatusEnum.approved
        balance.pending -= leave.days
        balance.used += leave.days

    elif action == "reject":
        leave.status = LeaveStatusEnum.rejected
        balance.pending -= leave.days

    else:
        raise Exception("Invalid action")

    leave.approved_by = approver_id
    leave.approved_at = datetime.utcnow()

    db.commit()
    db.refresh(leave)

    return leave


# =========================================================
# 🔹 CANCEL LEAVE
# =========================================================
def cancel_leave(db: Session, leave_id: int, employee_id: int):
    leave = db.query(LeaveRequest).get(leave_id)

    if not leave:
        raise Exception("Leave not found")

    if leave.employee_id != employee_id:
        raise Exception("Unauthorized")

    balance = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == leave.employee_id,
        LeaveBalance.leave_type_id == leave.leave_type_id,
        LeaveBalance.leave_cycle_id == leave.leave_cycle_id,
    ).first()

    if leave.status == LeaveStatusEnum.pending:
        balance.pending -= leave.days

    elif leave.status == LeaveStatusEnum.approved:
        balance.used -= leave.days

    leave.status = LeaveStatusEnum.cancelled

    db.commit()
    db.refresh(leave)

    return leave


# =========================================================
# 🔹 GET EMPLOYEE BALANCES
# =========================================================
def get_employee_balances(db: Session, employee_id: int):
    return db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == employee_id
    ).all()


# =========================================================
# 🔹 GET EMPLOYEE LEAVES
# =========================================================
def get_employee_leaves(db: Session, employee_id: int):
    return db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id
    ).order_by(LeaveRequest.created_at.desc()).all()


# =========================================================
# 🔹 LEAVE CYCLE MANAGEMENT
# =========================================================
def create_leave_cycle(
    db: Session,
    name: str,
    start_month: int,
    start_day: int,
    end_month: int,
    end_day: int,
):
    """Create a new leave cycle (HR only)"""
    cycle = LeaveCycle(
        name=name,
        start_month=start_month,
        start_day=start_day,
        end_month=end_month,
        end_day=end_day,
        is_active=True,
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return cycle


def update_leave_cycle(
    db: Session,
    cycle_id: int,
    name: str = None,
    start_month: int = None,
    start_day: int = None,
    end_month: int = None,
    end_day: int = None,
    is_active: bool = None,
):
    """Update leave cycle details"""
    cycle = db.query(LeaveCycle).get(cycle_id)
    if not cycle:
        raise Exception("Leave cycle not found")
    
    if name:
        cycle.name = name
    if start_month:
        cycle.start_month = start_month
    if start_day:
        cycle.start_day = start_day
    if end_month:
        cycle.end_month = end_month
    if end_day:
        cycle.end_day = end_day
    if is_active is not None:
        cycle.is_active = is_active
    
    db.commit()
    db.refresh(cycle)
    return cycle


def get_leave_cycle(db: Session, cycle_id: int):
    """Get leave cycle by ID"""
    return db.query(LeaveCycle).get(cycle_id)


def get_all_leave_cycles(db: Session):
    """Get all leave cycles"""
    return db.query(LeaveCycle).all()


def deactivate_leave_cycle(db: Session, cycle_id: int):
    """Deactivate a leave cycle"""
    cycle = db.query(LeaveCycle).get(cycle_id)
    if not cycle:
        raise Exception("Leave cycle not found")
    cycle.is_active = False
    db.commit()
    db.refresh(cycle)
    return cycle


# =========================================================
# 🔹 LEAVE TYPE MANAGEMENT
# =========================================================
def create_leave_type(
    db: Session,
    name: str,
    is_paid: bool,
    max_per_cycle: float,
    carry_forward: bool,
    max_carry_forward: float,
    leave_cycle_id: int,
):
    """Create a new leave type with limits (HR only)"""
    leave_type = LeaveType(
        name=name,
        is_paid=is_paid,
        max_per_cycle=max_per_cycle,
        carry_forward=carry_forward,
        max_carry_forward=max_carry_forward,
        leave_cycle_id=leave_cycle_id,
    )
    db.add(leave_type)
    db.commit()
    db.refresh(leave_type)
    return leave_type


def update_leave_type(
    db: Session,
    leave_type_id: int,
    name: str = None,
    is_paid: bool = None,
    max_per_cycle: float = None,
    carry_forward: bool = None,
    max_carry_forward: float = None,
):
    """Update leave type limits"""
    leave_type = db.query(LeaveType).get(leave_type_id)
    if not leave_type:
        raise Exception("Leave type not found")
    
    if name:
        leave_type.name = name
    if is_paid is not None:
        leave_type.is_paid = is_paid
    if max_per_cycle is not None:
        leave_type.max_per_cycle = max_per_cycle
    if carry_forward is not None:
        leave_type.carry_forward = carry_forward
    if max_carry_forward is not None:
        leave_type.max_carry_forward = max_carry_forward
    
    db.commit()
    db.refresh(leave_type)
    return leave_type


def get_leave_type(db: Session, leave_type_id: int):
    """Get leave type by ID"""
    return db.query(LeaveType).get(leave_type_id)


def get_all_leave_types(db: Session):
    """Get all leave types"""
    return db.query(LeaveType).all()


def get_leave_types_by_cycle(db: Session, cycle_id: int):
    """Get all leave types in a specific cycle"""
    return db.query(LeaveType).filter(
        LeaveType.leave_cycle_id == cycle_id
    ).all()


def delete_leave_type(db: Session, leave_type_id: int):
    """Delete a leave type (HR only)"""
    leave_type = db.query(LeaveType).get(leave_type_id)
    if not leave_type:
        raise Exception("Leave type not found")
    
    db.delete(leave_type)
    db.commit()
    return {"message": "Leave type deleted"}


# =========================================================
# 🔹 LEAVE BALANCE ALLOCATION (HR uses this)
# =========================================================
def allocate_leave_balance(
    db: Session,
    employee_id: int,
    leave_type_id: int,
    leave_cycle_id: int,
    allocated_days: float,
    cycle_start_date: date,
    cycle_end_date: date,
):
    """Allocate leave balance to an employee"""
    balance = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == employee_id,
        LeaveBalance.leave_type_id == leave_type_id,
        LeaveBalance.cycle_start_date == cycle_start_date,
    ).first()
    
    if balance:
        balance.allocated = allocated_days
    else:
        balance = LeaveBalance(
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            leave_cycle_id=leave_cycle_id,
            cycle_start_date=cycle_start_date,
            cycle_end_date=cycle_end_date,
            allocated=allocated_days,
            used=0,
            pending=0,
            carry_forward=0,
        )
        db.add(balance)
    
    db.commit()
    db.refresh(balance)
    return balance


def adjust_carry_forward(
    db: Session,
    employee_id: int,
    leave_type_id: int,
    cycle_start_date: date,
    carry_forward_days: float,
):
    """Adjust carry forward leaves from previous cycle"""
    balance = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == employee_id,
        LeaveBalance.leave_type_id == leave_type_id,
        LeaveBalance.cycle_start_date == cycle_start_date,
    ).first()
    
    if not balance:
        raise Exception("Leave balance not found for adjustment")
    
    balance.carry_forward = carry_forward_days
    db.commit()
    db.refresh(balance)
    return balance


def get_employee_balance_for_leave_type(
    db: Session,
    employee_id: int,
    leave_type_id: int,
    today: date = None,
):
    """Get current leave balance for an employee and leave type"""
    if today is None:
        today = date.today()
    
    leave_type = db.query(LeaveType).get(leave_type_id)
    if not leave_type:
        raise Exception("Leave type not found")
    
    cycle = leave_type.leave_cycle
    start_date, end_date = get_cycle_dates(cycle, today)
    
    balance = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == employee_id,
        LeaveBalance.leave_type_id == leave_type_id,
        LeaveBalance.cycle_start_date == start_date,
    ).first()
    
    return balance


# =========================================================
# 🔹 PENDING LEAVE REQUESTS (For Managers)
# =========================================================
def get_pending_leaves_for_approval(db: Session, approver_id: int):
    """Get all pending leave requests for a manager/approver"""
    return db.query(LeaveRequest).filter(
        LeaveRequest.status == LeaveStatusEnum.pending,
    ).all()


def get_leaves_by_status(db: Session, status: str):
    """Get leaves by status"""
    return db.query(LeaveRequest).filter(
        LeaveRequest.status == status
    ).all()