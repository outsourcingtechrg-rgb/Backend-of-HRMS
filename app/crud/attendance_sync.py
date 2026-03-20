from sqlalchemy.orm import Session
from app.models.attendanceSync import AttendanceSync
from app.schemas.attendance_sync import AttendanceSyncCreate, AttendanceSyncUpdate


def create_device(db: Session, data: AttendanceSyncCreate):
    device = AttendanceSync(**data.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def get_devices(db: Session):
    return db.query(AttendanceSync).all()


def get_device(db: Session, device_id: int):
    return db.query(AttendanceSync).filter(AttendanceSync.id == device_id).first()


def update_device(db: Session, device_id: int, data: AttendanceSyncUpdate):
    device = db.query(AttendanceSync).filter(AttendanceSync.id == device_id).first()

    if not device:
        return None

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(device, key, value)

    db.commit()
    db.refresh(device)

    return device


def delete_device(db: Session, device_id: int):
    device = db.query(AttendanceSync).filter(AttendanceSync.id == device_id).first()

    if not device:
        return None

    db.delete(device)
    db.commit()

    return device 

def get_device_by_id(db: Session, device_id: int):
    return db.query(AttendanceSync).filter(
        AttendanceSync.id == device_id
    ).first()
