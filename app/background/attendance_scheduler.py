# attendance_scheduler.py

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from zk import ZK

from app.models.attendance import Attendance, AttendanceModeEnum
from app.models.attendanceSync import AttendanceSync
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


# -----------------------------
# 🔹 Safe Insert (NO DUPLICATES)
# -----------------------------
def insert_attendance_safe(db: Session, records: list):
    if not records:
        return 0

    stmt = insert(Attendance).values(records)
    stmt = stmt.prefix_with("IGNORE")  # 🚀 prevents duplicate crash

    result = db.execute(stmt)
    return result.rowcount


# -----------------------------
# 🔹 Fetch from device
# -----------------------------
def fetch_device_attendance(device_ip: str, port: int = 4370, last_sync: datetime = None):
    zk = ZK(device_ip, port=port, timeout=20)
    conn = None
    records = []

    try:
        conn = zk.connect()
        conn.disable_device()

        users = conn.get_users()
        user_map = {str(u.user_id): u.name for u in users}

        logs = conn.get_attendance()

        for log in logs:
            # 🔥 Small buffer to avoid device clock issues
            if last_sync and log.timestamp <= (last_sync - timedelta(seconds=5)):
                continue

            records.append({
                "employee_id":     int(log.user_id),
                "employee_name":   user_map.get(str(log.user_id)),
                "attendance_date": log.timestamp.date(),
                "attendance_time": log.timestamp.time(),
                "punch":           bool(log.punch),
                "attendance_mode": AttendanceModeEnum.onsite,
                "synced_at":       datetime.utcnow(),
            })

    except Exception as e:
        logger.error(f"Device {device_ip} fetch error: {e}")

    finally:
        if conn:
            conn.enable_device()
            conn.disconnect()

    return records


# -----------------------------
# 🔹 Initial Sync (one-time)
# -----------------------------
def initial_sync(device_id: int):
    db: Session = SessionLocal()
    try:
        device = db.get(AttendanceSync, device_id)

        if not device or not device.is_enabled:
            return

        if device.last_synced_at is not None:
            logger.info(f"Device {device.device_ip} already seeded, skipping initial sync.")
            return

        logger.info(f"Initial full sync for device {device.device_ip}...")

        records = fetch_device_attendance(device.device_ip, last_sync=None)

        inserted = insert_attendance_safe(db, records)

        # ✅ Use latest device timestamp (IMPORTANT)
        if records:
            latest_time = max(
                datetime.combine(r["attendance_date"], r["attendance_time"])
                for r in records
            )
            device.last_synced_at = latest_time

        db.commit()

        logger.info(f"Device {device.device_ip} initial sync — {inserted} inserted.")

    except Exception as e:
        db.rollback()
        logger.error(f"Initial sync failed for device {device_id}: {e}")

    finally:
        db.close()


# -----------------------------
# 🔹 Incremental Sync
# -----------------------------
def incremental_sync(device_id: int):
    db: Session = SessionLocal()
    try:
        device = db.get(AttendanceSync, device_id)

        if not device or not device.is_enabled:
            return

        last_sync_time = device.last_synced_at

        records = fetch_device_attendance(
            device.device_ip,
            last_sync=last_sync_time
        )

        inserted = insert_attendance_safe(db, records)

        # ✅ Update using latest log timestamp
        if records:
            latest_time = max(
                datetime.combine(r["attendance_date"], r["attendance_time"])
                for r in records
            )
            device.last_synced_at = latest_time

        db.commit()

        logger.info(
            f"Device {device.device_ip} incremental sync — "
            f"{inserted} inserted, {len(records) - inserted} skipped."
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Incremental sync failed for device {device_id}: {e}")

    finally:
        db.close()


# -----------------------------
# 🔹 Scheduler Setup
# -----------------------------
def schedule_all_devices():
    db: Session = SessionLocal()

    try:
        devices = db.execute(
            select(AttendanceSync).where(AttendanceSync.is_enabled == True)
        ).scalars().all()

        device_list = [
            (d.id, d.device_ip, d.sync_interval_minutes)
            for d in devices
        ]

    finally:
        db.close()

    # 🔹 Phase 1: Initial Sync
    for device_id, device_ip, _ in device_list:
        initial_sync(device_id)

    # 🔹 Phase 2: Scheduler
    scheduler = BackgroundScheduler(
        executors={
            "default": ThreadPoolExecutor(
                max_workers=max(len(device_list), 1)
            )
        }
    )

    for device_id, device_ip, interval_minutes in device_list:
        scheduler.add_job(
            incremental_sync,
            "interval",
            minutes=interval_minutes,
            args=[device_id],
            id=f"incremental_sync_{device_id}",
            replace_existing=True,
            max_instances=1,  # 🚀 prevents overlapping runs
        )

        logger.info(
            f"Device {device_ip} scheduled every {interval_minutes} minutes."
        )

    scheduler.start()
    return scheduler