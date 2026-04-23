"""
leave/crud.py  –  All database operations for the leave module.
"""
from __future__ import annotations

import os
from datetime import date, datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException, status, UploadFile
from sqlalchemy import func, extract, and_
from sqlalchemy.orm import Session, joinedload

from app.models.Leaves import (
    LeavesCycle,
    LeaveType,
    LeaveTransaction,
    LeaveAttachment,
    LeaveStatus,
)
from app.schemas.leave import (
    LeaveCycleCreate,
    LeaveCycleUpdate,
    LeaveTypeCreate,
    LeaveTypeUpdate,
    LeaveApplicationCreate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UPLOAD_DIR = os.getenv("LEAVE_UPLOAD_DIR", "media/leave_attachments")


def _get_or_404(db: Session, model, record_id: int, label: str):
    obj = db.get(model, record_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return obj


def _active_cycle(db: Session) -> LeavesCycle:
    cycle = db.query(LeavesCycle).filter(LeavesCycle.is_active == True).first()
    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active leave cycle found",
        )
    return cycle


def _business_days(start: date, end: date) -> int:
    """Count weekdays between start and end (inclusive)."""
    from datetime import timedelta
    delta = (end - start).days + 1
    days = 0
    for i in range(delta):
        d = start + timedelta(days=i)
        if d.weekday() < 5:
            days += 1
    return max(days, 1)


def _taken_days(db: Session, employee_id: int, leave_type_id: int, cycle_id: int) -> int:
    result = (
        db.query(func.coalesce(func.sum(LeaveTransaction.requested_days), 0))
        .filter(
            LeaveTransaction.employee_id == employee_id,
            LeaveTransaction.leave_type_id == leave_type_id,
            LeaveTransaction.cycle_id == cycle_id,
            LeaveTransaction.status == LeaveStatus.APPROVED,
        )
        .scalar()
    )
    return int(result)


def _pending_days(db: Session, employee_id: int, leave_type_id: int, cycle_id: int) -> int:
    result = (
        db.query(func.coalesce(func.sum(LeaveTransaction.requested_days), 0))
        .filter(
            LeaveTransaction.employee_id == employee_id,
            LeaveTransaction.leave_type_id == leave_type_id,
            LeaveTransaction.cycle_id == cycle_id,
            LeaveTransaction.status == LeaveStatus.PENDING,
        )
        .scalar()
    )
    return int(result)


# ---------------------------------------------------------------------------
# Leave Cycles
# ---------------------------------------------------------------------------

def create_cycle(db: Session, payload: LeaveCycleCreate) -> LeavesCycle:
    cycle = LeavesCycle(**payload.model_dump())
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return cycle


def get_all_cycles(db: Session) -> List[LeavesCycle]:
    return db.query(LeavesCycle).order_by(LeavesCycle.start_date.desc()).all()


def get_active_cycle(db: Session) -> LeavesCycle:
    return _active_cycle(db)


def update_cycle(db: Session, cycle_id: int, payload: LeaveCycleUpdate) -> LeavesCycle:
    cycle = _get_or_404(db, LeavesCycle, cycle_id, "Leave cycle")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(cycle, field, value)
    db.commit()
    db.refresh(cycle)
    return cycle


def delete_cycle(db: Session, cycle_id: int) -> None:
    cycle = _get_or_404(db, LeavesCycle, cycle_id, "Leave cycle")
    db.delete(cycle)
    db.commit()


# ---------------------------------------------------------------------------
# Leave Types
# ---------------------------------------------------------------------------

def create_leave_type(db: Session, payload: LeaveTypeCreate) -> LeaveType:
    _get_or_404(db, LeavesCycle, payload.cycle_id, "Leave cycle")
    lt = LeaveType(**payload.model_dump())
    db.add(lt)
    db.commit()
    db.refresh(lt)
    return lt


def get_all_leave_types(db: Session) -> List[LeaveType]:
    return db.query(LeaveType).all()


def get_leave_types_by_cycle(db: Session, cycle_id: int) -> List[LeaveType]:
    return db.query(LeaveType).filter(LeaveType.cycle_id == cycle_id).all()


def update_leave_type(db: Session, type_id: int, payload: LeaveTypeUpdate) -> LeaveType:
    lt = _get_or_404(db, LeaveType, type_id, "Leave type")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(lt, field, value)
    db.commit()
    db.refresh(lt)
    return lt


def delete_leave_type(db: Session, type_id: int) -> None:
    lt = _get_or_404(db, LeaveType, type_id, "Leave type")
    db.delete(lt)
    db.commit()


# ---------------------------------------------------------------------------
# Leave Applications
# ---------------------------------------------------------------------------

def apply_leave(
    db: Session, employee_id: int, payload: LeaveApplicationCreate
) -> LeaveTransaction:
    cycle = _active_cycle(db)
    leave_type = _get_or_404(db, LeaveType, payload.leave_type_id, "Leave type")

    # Validate dates fall within cycle
    if not (cycle.start_date <= payload.start_date <= cycle.end_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave dates must fall within the active cycle",
        )

    requested_days = _business_days(payload.start_date, payload.end_date)

    # Min days check
    if requested_days < leave_type.min_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum leave duration is {leave_type.min_days} day(s)",
        )

    # Max per use check
    if requested_days > leave_type.max_per_use:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum per application is {leave_type.max_per_use} day(s)",
        )

    # Total cycle quota check (0 = unlimited)
    if leave_type.total_per_cycle > 0:
        taken = _taken_days(db, employee_id, leave_type.id, cycle.id)
        pending = _pending_days(db, employee_id, leave_type.id, cycle.id)
        if taken + pending + requested_days > leave_type.total_per_cycle:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exceeds total allowed leave ({leave_type.total_per_cycle} days/cycle)",
            )

    tx = LeaveTransaction(
        employee_id=employee_id,
        leave_type_id=leave_type.id,
        cycle_id=cycle.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        requested_days=requested_days,
        employee_note=payload.employee_note,
        status=LeaveStatus.PENDING,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def get_my_applications(db: Session, employee_id: int) -> List[LeaveTransaction]:
    return (
        db.query(LeaveTransaction)
        .options(joinedload(LeaveTransaction.leave_type))
        .filter(LeaveTransaction.employee_id == employee_id)
        .order_by(LeaveTransaction.requested_at.desc())
        .all()
    )


def get_application(db: Session, application_id: int) -> LeaveTransaction:
    tx = (
        db.query(LeaveTransaction)
        .options(
            joinedload(LeaveTransaction.leave_type),
            joinedload(LeaveTransaction.attachments),
        )
        .filter(LeaveTransaction.id == application_id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Application not found")
    return tx


def cancel_application(db: Session, application_id: int, employee_id: int) -> LeaveTransaction:
    tx = get_application(db, application_id)
    if tx.employee_id != employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your application")
    if tx.status != LeaveStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PENDING applications can be cancelled",
        )
    tx.status = LeaveStatus.CANCELLED
    db.commit()
    db.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# HR – Application Management
# ---------------------------------------------------------------------------

def get_all_applications(db: Session) -> List[LeaveTransaction]:
    return (
        db.query(LeaveTransaction)
        .options(joinedload(LeaveTransaction.leave_type))
        .order_by(LeaveTransaction.requested_at.desc())
        .all()
    )


def get_pending_applications(db: Session) -> List[LeaveTransaction]:
    return (
        db.query(LeaveTransaction)
        .options(joinedload(LeaveTransaction.leave_type))
        .filter(LeaveTransaction.status == LeaveStatus.PENDING)
        .order_by(LeaveTransaction.requested_at.asc())
        .all()
    )


def get_applications_by_employee(db: Session, employee_id: int) -> List[LeaveTransaction]:
    return (
        db.query(LeaveTransaction)
        .options(joinedload(LeaveTransaction.leave_type))
        .filter(LeaveTransaction.employee_id == employee_id)
        .order_by(LeaveTransaction.requested_at.desc())
        .all()
    )


def _review_application(
    db: Session,
    application_id: int,
    reviewer_id: int,
    new_status: LeaveStatus,
    hr_note: Optional[str],
) -> LeaveTransaction:
    tx = get_application(db, application_id)
    if tx.status != LeaveStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application is already {tx.status.value}",
        )
    tx.status = new_status
    tx.reviewed_by = reviewer_id
    tx.reviewed_at = datetime.utcnow()
    tx.hr_note = hr_note
    db.commit()
    db.refresh(tx)
    return tx


def approve_application(
    db: Session, application_id: int, reviewer_id: int, hr_note: Optional[str] = None
) -> LeaveTransaction:
    return _review_application(db, application_id, reviewer_id, LeaveStatus.APPROVED, hr_note)


def reject_application(
    db: Session, application_id: int, reviewer_id: int, hr_note: Optional[str] = None
) -> LeaveTransaction:
    return _review_application(db, application_id, reviewer_id, LeaveStatus.REJECTED, hr_note)


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

async def upload_attachment(
    db: Session,
    transaction_id: int,
    uploader_id: int,
    file: UploadFile,
    description: Optional[str] = None,
) -> LeaveAttachment:
    tx = _get_or_404(db, LeaveTransaction, transaction_id, "Leave application")

    # Validate file extension against leave type's allowed types
    leave_type = db.get(LeaveType, tx.leave_type_id)
    ext = os.path.splitext(file.filename or "")[-1].lstrip(".").lower()
    allowed = [e.strip() for e in (leave_type.allowed_file_types or "").split(",")]
    if allowed and ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not allowed. Allowed: {leave_type.allowed_file_types}",
        )

    # Save to disk
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    safe_name = f"{transaction_id}_{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    attachment = LeaveAttachment(
        transaction_id=transaction_id,
        file_name=file.filename,
        file_path=file_path,
        file_size=len(contents),
        file_type=file.content_type,
        file_extension=ext,
        description=description,
        uploaded_by=uploader_id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def get_attachments(db: Session, transaction_id: int) -> List[LeaveAttachment]:
    _get_or_404(db, LeaveTransaction, transaction_id, "Leave application")
    return (
        db.query(LeaveAttachment)
        .filter(LeaveAttachment.transaction_id == transaction_id)
        .all()
    )


def get_attachment(db: Session, attachment_id: int) -> LeaveAttachment:
    att = db.get(LeaveAttachment, attachment_id)
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return att


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def get_leave_summary(db: Session, employee_id: int):
    cycle = _active_cycle(db)
    leave_types = get_leave_types_by_cycle(db, cycle.id)

    summaries = []
    for lt in leave_types:
        taken = _taken_days(db, employee_id, lt.id, cycle.id)
        pending = _pending_days(db, employee_id, lt.id, cycle.id)
        allocated = lt.total_per_cycle
        remaining = max(allocated - taken - pending, 0) if allocated > 0 else -1  # -1 = unlimited

        summaries.append(
            {
                "leave_type_id": lt.id,
                "leave_type_name": lt.name,
                "total_allocated": allocated,
                "total_taken": taken,
                "total_pending": pending,
                "remaining": remaining,
            }
        )

    return {
        "employee_id": employee_id,
        "cycle_id": cycle.id,
        "cycle_name": cycle.name,
        "summaries": summaries,
    }


# ---------------------------------------------------------------------------
# Dashboard Stats
# ---------------------------------------------------------------------------

def get_dashboard_stats(db: Session):
    # Total approved leaves (days taken)
    total_taken = (
        db.query(func.coalesce(func.sum(LeaveTransaction.requested_days), 0))
        .filter(LeaveTransaction.status == LeaveStatus.APPROVED)
        .scalar()
    )

    # Pending count
    pending_count = (
        db.query(func.count(LeaveTransaction.id))
        .filter(LeaveTransaction.status == LeaveStatus.PENDING)
        .scalar()
    )

    # Approved vs Rejected
    approved_count = (
        db.query(func.count(LeaveTransaction.id))
        .filter(LeaveTransaction.status == LeaveStatus.APPROVED)
        .scalar()
    )
    rejected_count = (
        db.query(func.count(LeaveTransaction.id))
        .filter(LeaveTransaction.status == LeaveStatus.REJECTED)
        .scalar()
    )
    total_reviewed = approved_count + rejected_count
    ratio = round((approved_count / total_reviewed) * 100, 2) if total_reviewed else 0.0

    # Department usage – requires Employee model to have a department attribute
    # We do a raw join; if department is not available this returns empty.
    try:
        from app.models import employee as Employee  # local import to avoid circular
        dept_rows = (
            db.query(Employee.department, func.count(LeaveTransaction.id).label("total"))
            .join(LeaveTransaction, LeaveTransaction.employee_id == Employee.id)
            .filter(LeaveTransaction.status == LeaveStatus.APPROVED)
            .group_by(Employee.department)
            .all()
        )
        dept_usage = [{"department": r.department or "Unassigned", "total_leaves": r.total} for r in dept_rows]
    except Exception:
        dept_usage = []

    # Monthly trend (current year)
    current_year = datetime.utcnow().year
    monthly_rows = (
        db.query(
            extract("month", LeaveTransaction.start_date).label("month"),
            func.count(LeaveTransaction.id).label("total"),
        )
        .filter(
            LeaveTransaction.status == LeaveStatus.APPROVED,
            extract("year", LeaveTransaction.start_date) == current_year,
        )
        .group_by("month")
        .order_by("month")
        .all()
    )
    monthly_trend = [
        {"month": f"{current_year}-{int(r.month):02d}", "total_leaves": r.total}
        for r in monthly_rows
    ]

    return {
        "total_leaves_taken": int(total_taken),
        "pending_approvals": int(pending_count),
        "approved_vs_rejected": {
            "approved": int(approved_count),
            "rejected": int(rejected_count),
            "ratio": ratio,
        },
        "department_usage": dept_usage,
        "monthly_trend": monthly_trend,
    }