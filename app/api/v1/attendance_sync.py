
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