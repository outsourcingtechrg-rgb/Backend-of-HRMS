from fastapi import APIRouter

from app.api.v1.role import router as role
from app.api.v1.shift import router as shift
from app.api.v1.department import router as department
from app.api.v1.employee import router as employee
from app.api.v1.auth import router as auth
from app.api.v1.attendance import router as attendance
from app.api.v1.attendance_sync import router as attendanceSync
from app.api.v1.application import router as application
from app.api.v1.policies import router as policies
from app.api.v1.notice import router as notice
# from app.api.v1.sync import router as sync

router = APIRouter()
router.include_router(role, prefix="/roles", tags=["Roles"])
router.include_router(shift, prefix="/shifts", tags=["Shifts"])
router.include_router(department, prefix="/departments", tags=["Departments"])
router.include_router(employee, prefix="/employees", tags=["Employees"])
router.include_router(attendance, prefix="/attendance", tags=["Attendance"])
router.include_router(application, prefix="/applications", tags=["Applications"])
router.include_router(auth, prefix="/auth", tags=["Authentication"])
router.include_router(policies, prefix="/policies", tags=["Policies"])
router.include_router(notice, prefix="/notices", tags=["Notices"])
router.include_router(attendanceSync, prefix="/attendance/sync", tags=["Attendance Sync"])
