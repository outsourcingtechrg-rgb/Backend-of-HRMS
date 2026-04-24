from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.employee import Employee
from app.crud import leave as crud
from app.schemas.leave import (
    DashboardStatsOut,
    LeaveApplicationCreate,
    LeaveApplicationOut,
    LeaveAttachmentOut,
    LeaveCycleCreate,
    LeaveCycleOut,
    LeaveCycleUpdate,
    LeaveSummaryOut,
    LeaveReviewRequest,
    LeaveTypeCreate,
    LeaveTypeOut,
    LeaveTypeUpdate,
)

router = APIRouter()

# ===========================
# MY LEAVES
# ===========================

@router.post(
    "/applications",
    response_model=LeaveApplicationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Apply for leave",
)
def apply_leave(
    payload: LeaveApplicationCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return crud.apply_leave(db, current_user.id, payload)


@router.get(
    "/applications/me",
    response_model=List[LeaveApplicationOut],
    summary="Get my leave applications",
)
def my_applications(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return crud.get_my_applications(db, current_user.id)


@router.get(
    "/applications/{id}",
    response_model=LeaveApplicationOut,
    summary="Get single application",
)
def get_application(
    id: int,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    return crud.get_application(db, id)


@router.post(
    "/applications/{id}/cancel",
    response_model=LeaveApplicationOut,
    summary="Cancel my pending application",
)
def cancel_application(
    id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return crud.cancel_application(db, id, current_user.id)


# ===========================
# ATTACHMENTS (employee-facing)
# ===========================

@router.post(
    "/applications/{id}/attachments",
    response_model=LeaveAttachmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload attachment for an application",
)
async def upload_attachment(
    id: int,
    file: UploadFile = File(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return await crud.upload_attachment(db, id, current_user.id, file, description)


@router.get(
    "/applications/{id}/attachments",
    response_model=List[LeaveAttachmentOut],
    summary="List attachments for an application",
)
def get_attachments(
    id: int,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    return crud.get_attachments(db, id)


@router.get(
    "/attachments/{attachment_id}/download",
    summary="Download an attachment file",
)
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    att = crud.get_attachment(db, attachment_id)
    return FileResponse(
        path=att.file_path,
        filename=att.file_name,
        media_type=att.file_type or "application/octet-stream",
    )


# ===========================
# SUMMARY
# ===========================

@router.get(
    "/summary/me",
    response_model=LeaveSummaryOut,
    summary="Get my leave summary for the active cycle",
)
def my_summary(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return crud.get_leave_summary(db, current_user.id)


@router.get(
    "/summary/employee/{employee_id}",
    response_model=LeaveSummaryOut,
    summary="[HR] Get leave summary for a specific employee",
)
def employee_summary(
    employee_id: int,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    return crud.get_leave_summary(db, employee_id)


# ===========================
# LEAVE MANAGEMENT – Applications
# ===========================

@router.get(
    "/applications",
    response_model=List[LeaveApplicationOut],
    summary="[HR] Get all leave applications",
)
def all_applications(
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    return crud.get_all_applications(db)


@router.get(
    "/applications/pending",
    response_model=List[LeaveApplicationOut],
    summary="[HR] Get all pending applications",
)
def pending_applications(
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    return crud.get_pending_applications(db)


@router.get(
    "/applications/employee/{employee_id}",
    response_model=List[LeaveApplicationOut],
    summary="[HR] Get applications by employee",
)
def applications_by_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    return crud.get_applications_by_employee(db, employee_id)


@router.post(
    "/applications/{id}/approve",
    response_model=LeaveApplicationOut,
    summary="[HR] Approve a leave application",
)
def approve_application(
    id: int,
    body: LeaveReviewRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return crud.approve_application(db, id, current_user.id, body.hr_note)


@router.post(
    "/applications/{id}/reject",
    response_model=LeaveApplicationOut,
    summary="[HR] Reject a leave application",
)
def reject_application(
    id: int,
    body: LeaveReviewRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return crud.reject_application(db, id, current_user.id, body.hr_note)


@router.get(
    "/management/applications/{id}/attachments",
    response_model=List[LeaveAttachmentOut],
    summary="[HR] View attachments for any application",
)
def hr_get_attachments(
    id: int,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    return crud.get_attachments(db, id)


@router.get(
    "/management/attachments/{attachment_id}/download",
    summary="[HR] Download any attachment",
)
def hr_download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    att = crud.get_attachment(db, attachment_id)
    return FileResponse(
        path=att.file_path,
        filename=att.file_name,
        media_type=att.file_type or "application/octet-stream",
    )


# ===========================
# LEAVE TYPES
# ===========================

@router.post(
    "/types",
    response_model=LeaveTypeOut,
    status_code=status.HTTP_201_CREATED,
    summary="[HR] Create a leave type",
)
def create_leave_type(
    payload: LeaveTypeCreate,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    return crud.create_leave_type(db, payload)


@router.get(
    "/types",
    response_model=List[LeaveTypeOut],
    summary="Get all leave types",
)
def all_leave_types(db: Session = Depends(get_db)):
    return crud.get_all_leave_types(db)


@router.get(
    "/types/cycle/{cycle_id}",
    response_model=List[LeaveTypeOut],
    summary="Get leave types by cycle",
)
def leave_types_by_cycle(cycle_id: int, db: Session = Depends(get_db)):
    return crud.get_leave_types_by_cycle(db, cycle_id)


@router.get(
    "/types/employees",
    response_model=List[LeaveTypeOut],
    summary="Get leave types available to me based on my gender",
)
def my_available_leave_types(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return crud.get_available_leave_types(db, current_user.id)


@router.patch(
    "/types/{type_id}",
    response_model=LeaveTypeOut,
    summary="[HR] Update a leave type",
)
def update_leave_type(
    type_id: int,
    payload: LeaveTypeUpdate,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    return crud.update_leave_type(db, type_id, payload)


@router.delete(
    "/types/{type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[HR] Delete a leave type",
)
def delete_leave_type(
    type_id: int,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    crud.delete_leave_type(db, type_id)


# ===========================
# LEAVE CYCLES
# ===========================

@router.post(
    "/cycles",
    response_model=LeaveCycleOut,
    status_code=status.HTTP_201_CREATED,
    summary="[HR] Create a leave cycle",
)
def create_cycle(
    payload: LeaveCycleCreate,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    return crud.create_cycle(db, payload)


@router.get(
    "/cycles",
    response_model=List[LeaveCycleOut],
    summary="Get all leave cycles",
)
def all_cycles(db: Session = Depends(get_db)):
    return crud.get_all_cycles(db)


@router.get(
    "/cycles/active",
    response_model=LeaveCycleOut,
    summary="Get the currently active cycle",
)
def active_cycle(db: Session = Depends(get_db)):
    return crud.get_active_cycle(db)


@router.patch(
    "/cycles/{cycle_id}",
    response_model=LeaveCycleOut,
    summary="[HR] Update a leave cycle",
)
def update_cycle(
    cycle_id: int,
    payload: LeaveCycleUpdate,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    return crud.update_cycle(db, cycle_id, payload)


@router.delete(
    "/cycles/{cycle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[HR] Delete a leave cycle",
)
def delete_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    crud.delete_cycle(db, cycle_id)


# ===========================
# DASHBOARD
# ===========================

@router.get(
    "/dashboard/stats",
    response_model=DashboardStatsOut,
    summary="[HR] Get dashboard widget stats",
)
def dashboard_stats(
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_user),
):
    return crud.get_dashboard_stats(db)