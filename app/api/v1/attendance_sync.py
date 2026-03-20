# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from datetime import datetime

# from app.core.database import get_db
# from app.background.deletedFiles.attendance_sync_service import sync_attendance
# from app.models.attendanceSync import AttendanceSync
# from app.schemas.sync_settings import SyncSettingsRead, SyncSettingsUpdate

# router = APIRouter()

# DEVICE_IP = "172.16.32.184"


# @router.post("/attendance-sync/run")
# def run_sync(db: Session = Depends(get_db)):
#     """Manually trigger attendance sync from ZKT device."""
#     try:
#         result = sync_attendance(db)
#         return {
#             "success": True,
#             "message": "Sync completed",
#             "data": result
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/attendance-sync/status", response_model=SyncSettingsRead)
# def sync_status(db: Session = Depends(get_db)):
#     """Get current sync status and settings."""
#     sync_row = db.query(AttendanceSync).filter(
#         AttendanceSync.device_ip == DEVICE_IP
#     ).first()

#     if not sync_row:
#         raise HTTPException(status_code=404, detail="Sync settings not found")

#     return sync_row

 
# @router.patch("/attendance-sync/settings", response_model=SyncSettingsRead)
# def update_sync_settings(
#     settings: SyncSettingsUpdate,
#     db: Session = Depends(get_db)
# ):
#     """Update sync settings (interval, enabled status)."""
#     sync_row = db.query(AttendanceSync).filter(
#         AttendanceSync.device_ip == DEVICE_IP
#     ).first()

#     if not sync_row:
#         raise HTTPException(status_code=404, detail="Sync settings not found")

#     if settings.sync_interval_minutes is not None:
#         if settings.sync_interval_minutes < 1:
#             raise HTTPException(status_code=400, detail="Interval must be at least 1 minute")
#         sync_row.sync_interval_minutes = settings.sync_interval_minutes

#     if settings.is_enabled is not None:
#         sync_row.is_enabled = settings.is_enabled

#     sync_row.updated_at = datetime.utcnow()
#     db.commit()
#     db.refresh(sync_row)

#     return sync_row


# @router.post("/attendance-sync/reset-sync-time")
# def reset_sync_time(db: Session = Depends(get_db)):
#     """Reset last sync to get all attendance from start."""
#     sync_row = db.query(AttendanceSync).filter(
#         AttendanceSync.device_ip == DEVICE_IP
#     ).first()

#     if not sync_row:
#         raise HTTPException(status_code=404, detail="Sync settings not found")

#     sync_row.last_synced_at = datetime(2020, 1, 1)
#     db.commit()

#     return {
#         "success": True,
#         "message": "Sync time reset to 2020-01-01",
#         "last_synced_at": sync_row.last_synced_at
#     }


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.attendance_sync import (
    AttendanceSyncCreate,
    AttendanceSyncUpdate,
    AttendanceSyncResponse,
)
from app.crud import attendance_sync as crud

router = APIRouter()


@router.post("/", response_model=AttendanceSyncResponse)
def create_device(data: AttendanceSyncCreate, db: Session = Depends(get_db)):
    return crud.create_device(db, data)


@router.get("/", response_model=List[AttendanceSyncResponse])
def list_devices(db: Session = Depends(get_db)):
    return crud.get_devices(db)


@router.get("/{device_id}", response_model=AttendanceSyncResponse)
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = crud.get_device(db, device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return device


@router.put("/{device_id}", response_model=AttendanceSyncResponse)
def update_device(device_id: int, data: AttendanceSyncUpdate, db: Session = Depends(get_db)):
    device = crud.update_device(db, device_id, data)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return device


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = crud.delete_device(db, device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return {"message": "Device deleted successfully"}