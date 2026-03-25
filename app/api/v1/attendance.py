"""
attendance_router.py

ID semantics
────────────
  /me/* endpoints:
    employee_id = Employee.id  (DB PK from JWT)
    CRUD resolves → Employee.employee_id (machine ID) internally.

  /admin/* endpoints:
    Return enriched logical records filtered to system employees only.
    ZKT ghost entries (machine IDs with no Employee row) are excluded.

  Raw admin endpoints (/ /employee/{id} etc.):
    employee_id = Attendance.employee_id = Employee.employee_id (machine ID).
    Results always filtered to known employees via _known_machine_ids().

Route ordering — FastAPI matches top-to-bottom:
  /me/today, /me/summary, /me   must come BEFORE  /{attendance_id}
  /admin/*                      must come BEFORE  /{attendance_id}
  /sync/status                  must come BEFORE  /{attendance_id}
"""

from datetime import datetime, date
from typing import Optional, List, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import attendance as attendance_crud
from app.models.attendance import Attendance
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceUpdate,
    AttendanceOut,
    AttendanceRead,
    AttendanceBulkCreate,
    AttendanceSyncStatus,
    AttendanceRecord,
    AttendanceSummary,
)


router = APIRouter()


# =========================================================
# USER  /me/*  (Employee.id from JWT)
# MUST be declared above /{attendance_id}
# =========================================================

@router.get("/me", response_model=list[AttendanceRecord])
def my_attendance(
    employee_id: int = Query(..., description="Employee.id from JWT"),
    month: Optional[str] = Query(None, description="YYYY-MM"),
    db: Session = Depends(get_db),
):
    """
    Monthly attendance for the signed-in employee.
    Returns [] when the employee has no ZKT machine enrollment.
    """
    return attendance_crud.get_my_attendance(
        db=db, employee_id=employee_id, month=month
    )


@router.get("/me/today", response_model=AttendanceRecord | None)
def my_attendance_today(
    employee_id: int = Query(..., description="Employee.id from JWT"),
    db: Session = Depends(get_db),
):
    """
    Today's logical attendance record.
    Returns null when outside the shift window or not enrolled.
    """
    return attendance_crud.get_today_attendance(db=db, employee_id=employee_id)


@router.get("/me/summary", response_model=AttendanceSummary)
def my_attendance_summary(
    employee_id: int = Query(..., description="Employee.id from JWT"),
    month: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
):
    """Monthly summary: Present / Late / Early / Absent / Leave / Rate."""
    return attendance_crud.get_attendance_summary(
        db=db, employee_id=employee_id, month=month
    )


# =========================================================
# ADMIN  /admin/*
# Enriched logical records for HR / CEO views.
# Filtered to system employees only — no ZKT ghost entries.
# MUST be declared above /{attendance_id}
# =========================================================

@router.get("/admin/records")
def admin_attendance_records(
    month: Optional[str] = Query(
        None,
        description="YYYY-MM — strongly recommended to avoid huge payloads",
    ),
    employee_id: Optional[int] = Query(
        None,
        description="Filter to one employee by Employee.id (DB PK)",
    ),
    department_id: Optional[int] = Query(
        None,
        description="Filter to one department by Department.id",
    ),
    status: Optional[str] = Query(
        None,
        description="Present | Late | Early | Absent | Leave",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> Any:
    """
    Enriched logical attendance records for admin/HR views.

    Each record includes:
      id, employee_id (machine), employee_db_id (Employee.id),
      employee_name, f_name, l_name, designation,
      department_id, department_name, employment_status, image,
      date, status, in_time, out_time, hours, attendance_mode

    Only employees present in the system Employee table are returned.
    ZKT entries for ex-employees or test machine slots are excluded.
    """
    return attendance_crud.get_admin_records(
        db=db,
        month=month,
        employee_db_id=employee_id,
        department_id=department_id,
        status_filter=status,
        skip=skip,
        limit=limit,
    )


@router.get("/admin/summary")
def admin_attendance_summary(
    month: str = Query(..., description="YYYY-MM"),
    department_id: Optional[int] = Query(None, description="Scope to one department"),
    db: Session = Depends(get_db),
) -> Any:
    """
    Organisation-wide (or department-scoped) attendance summary.

    Returns:
      {
        present, late, early, absent, leave,
        total_records, total_employees, rate,
        by_department: [{ department_id, department_name, present, total, rate }]
      }

    Counts only employees that exist in the Employee table.
    """
    return attendance_crud.get_admin_summary(
        db=db,
        month=month,
        department_id=department_id,
    )


# =========================================================
# SYNC STATUS — BEFORE /{attendance_id}
# =========================================================

@router.get("/sync/status", response_model=AttendanceSyncStatus)
def get_sync_status(db: Session = Depends(get_db)):
    """Last ZKT sync time and total synced record count."""
    last_synced  = attendance_crud.get_last_synced_time(db)
    total_synced = (
        db.query(Attendance)
        .filter(Attendance.synced_at.isnot(None))
        .count()
    )
    return AttendanceSyncStatus(
        last_synced_at=last_synced,
        total_records_synced=total_synced,
        message="Sync status retrieved successfully",
    )


# =========================================================
# RAW PUNCH ROWS — CREATE / LIST
# =========================================================

@router.post("/", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
def create_attendance(
    attendance_in: AttendanceCreate,
    db: Session = Depends(get_db),
):
    """Insert one raw punch row (single device event)."""
    return attendance_crud.create_attendance(db, attendance_in)


@router.post("/bulk", response_model=List[AttendanceOut], status_code=status.HTTP_201_CREATED)
def create_bulk_attendance(
    bulk_data: AttendanceBulkCreate,
    db: Session = Depends(get_db),
):
    """Bulk-insert raw punch rows from a ZKT device sync."""
    if not bulk_data.records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No records provided",
        )
    return attendance_crud.bulk_create_attendance(db, bulk_data.records)


@router.get("/", response_model=List[AttendanceRead])
def list_attendance(
    employee_id: Optional[int] = Query(
        None,
        description="Machine ID (Employee.employee_id). Omit = all known employees.",
    ),
    attendance_date: Optional[date] = Query(None),
    month: Optional[str] = Query(None, description="YYYY-MM"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    List raw punch rows filtered to known system employees.
    ZKT ghost entries are excluded automatically.
    """
    from calendar import monthrange as _mr

    start_date: Optional[date] = None
    end_date:   Optional[date] = None

    if month:
        year, mon  = map(int, month.split("-"))
        last_day   = _mr(year, mon)[1]
        start_date = date(year, mon, 1)
        end_date   = date(year, mon, last_day)

    q = db.query(Attendance)

    if employee_id is not None:
        q = q.filter(Attendance.employee_id == employee_id)
    else:
        known = attendance_crud._known_machine_ids(db)
        if not known:
            return []
        q = q.filter(Attendance.employee_id.in_(known))

    if attendance_date:
        q = q.filter(Attendance.attendance_date == attendance_date)
    elif start_date and end_date:
        q = q.filter(Attendance.attendance_date.between(start_date, end_date))

    return (
        q.order_by(Attendance.attendance_date.desc())
         .offset(skip)
         .limit(limit)
         .all()
    )


@router.get("/employee/{employee_id}/date/{attendance_date}", response_model=List[AttendanceRead])
def get_employee_attendance_by_date(
    employee_id: int,
    attendance_date: date,
    db: Session = Depends(get_db),
):
    """Raw punch rows for one employee (machine ID) on one date."""
    return attendance_crud.get_attendance_by_employee_and_date(
        db, employee_id, attendance_date
    )


@router.get("/employee/{employee_id}", response_model=List[AttendanceRead])
def get_employee_attendance(
    employee_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """All raw punch rows for one employee (machine ID)."""
    return attendance_crud.get_attendances(
        db, employee_id=employee_id, skip=skip, limit=limit
    )


@router.get("/id/{attendance_id}", response_model=AttendanceRead)
def get_attendance_by_id(
    attendance_id: int,
    db: Session = Depends(get_db),
):
    """Single raw punch row by primary key."""
    obj = attendance_crud.get_attendance_by_id(db, attendance_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Attendance record not found")
    return obj


# =========================================================
# UPDATE / DELETE — after all named routes
# =========================================================

@router.put("/{attendance_id}", response_model=AttendanceRead)
def update_attendance(
    attendance_id: int,
    attendance_in: AttendanceUpdate,
    db: Session = Depends(get_db),
):
    obj = attendance_crud.get_attendance_by_id(db, attendance_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Attendance record not found")
    return attendance_crud.update_attendance(db, attendance_id, attendance_in)


@router.delete("/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
):
    if not attendance_crud.delete_attendance(db, attendance_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Attendance record not found")
    return None