from datetime import datetime, date
from typing import Optional, List

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
# 🔹 USER (FRONTEND APIs)  ✅ MUST BE ABOVE /{id}
# =========================================================

@router.get("/me", response_model=list[AttendanceRecord])
def my_attendance(
    employee_id: int = Query(..., description="Employee ID"),
    month: Optional[str] = Query(None, description="Format: YYYY-MM"),
    db: Session = Depends(get_db),
):
    """Get employee attendance (acts like 'me')"""
    return attendance_crud.get_my_attendance(
        db=db,
        employee_id=employee_id,
        month=month
    )

@router.get("/me/today", response_model=AttendanceRecord | None)
def my_attendance_today(
    employee_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Get today's attendance"""
    return attendance_crud.get_today_attendance(
        db=db,
        employee_id=employee_id
    )

@router.get("/me/summary", response_model=AttendanceSummary)
def my_attendance_summary(
    employee_id: int = Query(...),
    month: str = Query(..., description="Format: YYYY-MM"),
    db: Session = Depends(get_db),
):
    """Get monthly summary"""
    return attendance_crud.get_attendance_summary(
        db=db,
        employee_id=employee_id,
        month=month
    )

# =========================================================
# 🔹 RAW ATTENDANCE (DEVICE / ADMIN)
# =========================================================

@router.post("/", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
def create_attendance(
    attendance_in: AttendanceCreate,
    db: Session = Depends(get_db),
):
    """Create a new attendance record"""
    return attendance_crud.create_attendance(db, attendance_in)


@router.post("/bulk", response_model=List[AttendanceOut], status_code=status.HTTP_201_CREATED)
def create_bulk_attendance(
    bulk_data: AttendanceBulkCreate,
    db: Session = Depends(get_db),
):
    """Bulk create attendance records (ZKT sync)"""
    if not bulk_data.records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No records provided"
        )
    return attendance_crud.bulk_create_attendance(db, bulk_data.records)


@router.get("/", response_model=List[AttendanceRead])
def list_attendance(
    employee_id: Optional[int] = Query(None),
    attendance_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List attendance records with filters"""
    return attendance_crud.get_attendances(
        db,
        employee_id=employee_id,
        attendance_date=attendance_date,
        skip=skip,
        limit=limit
    )


@router.get("/employee/{employee_id}/date/{attendance_date}", response_model=List[AttendanceRead])
def get_employee_attendance_by_date(
    employee_id: int,
    attendance_date: date,
    db: Session = Depends(get_db),
):
    """Get attendance for an employee on a specific date"""
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
    """Get all attendance for an employee"""
    return attendance_crud.get_attendances(
        db,
        employee_id=employee_id,
        skip=skip,
        limit=limit
    )


# ✅ FIXED ROUTE (no conflict with /me)
@router.get("/id/{attendance_id}", response_model=AttendanceRead)
def get_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
):
    """Get attendance by ID"""
    attendance = attendance_crud.get_attendance_by_id(db, attendance_id)
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )
    return attendance


@router.put("/{attendance_id}", response_model=AttendanceRead)
def update_attendance(
    attendance_id: int,
    attendance_in: AttendanceUpdate,
    db: Session = Depends(get_db),
):
    """Update attendance"""
    attendance = attendance_crud.get_attendance_by_id(db, attendance_id)
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )

    return attendance_crud.update_attendance(
        db, attendance_id, attendance_in
    )


@router.delete("/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
):
    """Delete attendance"""
    success = attendance_crud.delete_attendance(db, attendance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )

    return None


# =========================================================
# 🔹 SYNC STATUS
# =========================================================

@router.get("/sync/status", response_model=AttendanceSyncStatus)
def get_sync_status(db: Session = Depends(get_db)):
    """Get sync status"""
    last_synced = attendance_crud.get_last_synced_time(db)
    total_synced = db.query(Attendance).filter(
        Attendance.synced_at != None
    ).count()

    return AttendanceSyncStatus(
        last_synced_at=last_synced,
        total_records_synced=total_synced,
        message="Sync status retrieved successfully"
    )