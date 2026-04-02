"""
app/routers/notice_router.py

Notice Board endpoints.

Route map
─────────
  GET  /notices/stats          → NoticeStats (admin)
  GET  /notices/my             → List[EmployeeNoticeItem] (employee board)
  GET  /notices/my/acked       → List[int]  (acked notice IDs)
  GET  /notices/               → List[NoticeListItem]
  GET  /notices/{id}           → NoticeOut
  POST /notices/               → NoticeOut  (create — authorized only)
  PATCH /notices/{id}          → NoticeOut  (edit — creator or admin)
  DELETE /notices/{id}         → 204        (soft delete — creator or admin)
  POST /notices/{id}/pin       → NoticeOut  (toggle pin — admin)
  POST /notices/{id}/toggle    → NoticeOut  (toggle active — admin)
  POST /notices/{id}/acknowledge → AcknowledgeOut (any employee)

Auth — who can CREATE/EDIT/DELETE notices
──────────────────────────────────────────
  level 1  Super Admin
  level 2  CEO
  level 3  HR Admin
  level 4  HR
  level 6  Department Head  ← can only create/edit notices for their own dept
  (All other levels: read + acknowledge only)

Department Head restriction
───────────────────────────
  When a Department Head (level 6) creates a notice, the audience_type
  is forced to "departments" and department_ids is forced to contain
  only their own department_id. This is enforced in the router.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.crud import notice as notice_crud
from app.schemas.notice import (
    NoticeCreate, NoticeUpdate,
    NoticeOut, NoticeListItem,
    NoticeStats, AcknowledgeOut,
    EmployeeNoticeItem,
)

router = APIRouter()

# ─── Auth helpers ────────────────────────────────────────────────

def _actor(current_user):
    role  = getattr(current_user, "role", None)
    level = getattr(role, "level", 99) if role else 99
    emp   = current_user
    dept_id = getattr(emp, "department_id", None)
    return int(getattr(emp, "id")), int(level), dept_id


def _blank_to_none(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    return v or None


def _parse_bool(v: Optional[str]) -> Optional[bool]:
    v = _blank_to_none(v)
    if v is None:
        return None
    if v.lower() in {"true", "1", "yes"}:
        return True
    if v.lower() in {"false", "0", "no"}:
        return False
    raise HTTPException(422, "Expected boolean value")


# Levels that can create / manage notices
CAN_MANAGE = {1, 2, 3, 4, 6}  # 6 = Department Head

def _require_manager(level: int):
    if level not in CAN_MANAGE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage notices",
        )


def _require_admin(level: int):
    """Pin / toggle-active require at least HR level."""
    if level not in {1, 2, 3, 4}:
        raise HTTPException(403, "HR Admin or above required")


def _get_employee_context(db: Session, employee_id: int):
    """Return (dept_id, dept_name, role_name) for the employee."""
    try:
        from app.models.employee import Employee
        from app.models.department import Department
        from app.models.role import Role

        emp = db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.is_deleted == False,
        ).first()
        if not emp:
            return None, None, None

        dept_id, role_name = None, None
        if emp.department_id:
            dept = db.query(Department).filter(Department.id == emp.department_id).first()
            dept_id = dept.id if dept else None
        if emp.role_id:
            role = db.query(Role).filter(Role.id == emp.role_id).first()
            role_name = role.name if role else None

        return dept_id, None, role_name
    except Exception:
        return None, None, None


# ═══════════════════════════════════════════════════════════════════
# STATS  (above /{id})
# ═══════════════════════════════════════════════════════════════════

@router.get("/stats", response_model=NoticeStats)
def get_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _, level, _ = _actor(current_user)
    _require_admin(level)
    return notice_crud.get_notice_stats(db)


# ═══════════════════════════════════════════════════════════════════
# MY NOTICES  (employee board — above /{id})
# ═══════════════════════════════════════════════════════════════════

@router.get("/my", response_model=List[EmployeeNoticeItem])
def my_notices(
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    search:   Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Returns active, non-expired notices scoped to the employee's
    audience (all / their dept / their role / selective by id).
    Includes acknowledged=True/False per notice.
    """
    actor_id, _, _ = _actor(current_user)
    dept_id, _, role_name = _get_employee_context(db, actor_id)

    return notice_crud.get_my_notices(
        db                  = db,
        employee_id         = actor_id,
        employee_dept_id    = dept_id,
        employee_role_name  = role_name,
        category            = _blank_to_none(category),
        priority            = _blank_to_none(priority),
        search              = _blank_to_none(search),
    )


@router.get("/my/acked", response_model=List[int])
def my_acked_notices(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    actor_id, _, _ = _actor(current_user)
    return notice_crud.get_employee_acked_notice_ids(db, actor_id)


# ═══════════════════════════════════════════════════════════════════
# LIST  (admin view — all notices)
# ═══════════════════════════════════════════════════════════════════

@router.get("/", response_model=List[NoticeListItem])
def list_notices(
    category:      Optional[str] = Query(None),
    priority:      Optional[str] = Query(None),
    audience_type: Optional[str] = Query(None),
    is_active:     Optional[str] = Query(None),
    search:        Optional[str] = Query(None),
    skip:          int           = Query(0, ge=0),
    limit:         int           = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    actor_id, level, dept_id = _actor(current_user)
    is_admin = level in {1, 2, 3, 4, 6}  # all managers can see list

    dept_id_ctx, _, role_name_ctx = _get_employee_context(db, actor_id)

    return notice_crud.list_notices(
        db                  = db,
        is_admin            = is_admin,
        employee_dept_id    = dept_id_ctx,
        employee_role_name  = role_name_ctx,
        employee_id         = actor_id,
        category            = _blank_to_none(category),
        priority            = _blank_to_none(priority),
        audience_type       = _blank_to_none(audience_type) if is_admin else None,
        is_active           = _parse_bool(is_active) if is_admin else True,
        search              = _blank_to_none(search),
        skip                = skip,
        limit               = limit,
    )


# ═══════════════════════════════════════════════════════════════════
# GET SINGLE
# ═══════════════════════════════════════════════════════════════════

@router.get("/{notice_id}", response_model=NoticeOut)
def get_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    actor_id, level, _ = _actor(current_user)
    is_admin = level in {1, 2, 3, 4, 6}

    result = notice_crud.get_notice_detail(db, notice_id)
    if not result:
        raise HTTPException(404, "Notice not found")

    # Non-managers can only see active notices
    if not is_admin and not result.is_active:
        raise HTTPException(403, "This notice is not available")

    return result


# ═══════════════════════════════════════════════════════════════════
# CREATE
# ═══════════════════════════════════════════════════════════════════

@router.post("/", response_model=NoticeOut, status_code=status.HTTP_201_CREATED)
def create_notice(
    data: NoticeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    actor_id, level, _ = _actor(current_user)
    _require_manager(level)

    # Department Head restriction: can only target own department
    if level == 6:
        dept_id_ctx, _, _ = _get_employee_context(db, actor_id)
        if not dept_id_ctx:
            raise HTTPException(400, "Your department could not be determined")
        # Force audience to their department
        data = data.model_copy(update={
            "audience_type": "departments",
            "department_ids": [dept_id_ctx],
        })

    return notice_crud.create_notice(db, data, created_by=actor_id)


# ═══════════════════════════════════════════════════════════════════
# UPDATE
# ═══════════════════════════════════════════════════════════════════

@router.patch("/{notice_id}", response_model=NoticeOut)
def update_notice(
    notice_id: int,
    data: NoticeUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    actor_id, level, _ = _actor(current_user)
    _require_manager(level)

    # Department Head can only edit notices they created
    existing = notice_crud.get_notice_by_id_raw(db, notice_id)
    if not existing:
        raise HTTPException(404, "Notice not found")
    if level == 6 and existing.created_by != actor_id:
        raise HTTPException(403, "You can only edit notices you created")

    # Department Head cannot change audience away from their dept
    if level == 6 and data.department_ids is not None:
        dept_id_ctx, _, _ = _get_employee_context(db, actor_id)
        data = data.model_copy(update={"department_ids": [dept_id_ctx]})

    result = notice_crud.update_notice(db, notice_id, data)
    if not result:
        raise HTTPException(404, "Notice not found")
    return result


# ═══════════════════════════════════════════════════════════════════
# DELETE
# ═══════════════════════════════════════════════════════════════════

@router.delete("/{notice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    actor_id, level, _ = _actor(current_user)
    _require_manager(level)

    existing = notice_crud.get_notice_by_id_raw(db, notice_id)
    if not existing:
        raise HTTPException(404, "Notice not found")
    if level == 6 and existing.created_by != actor_id:
        raise HTTPException(403, "You can only delete notices you created")

    if not notice_crud.delete_notice(db, notice_id):
        raise HTTPException(404, "Notice not found")
    return None


# ═══════════════════════════════════════════════════════════════════
# PIN TOGGLE
# ═══════════════════════════════════════════════════════════════════

@router.post("/{notice_id}/pin", response_model=NoticeOut)
def toggle_pin(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _, level, _ = _actor(current_user)
    _require_admin(level)
    result = notice_crud.toggle_pin(db, notice_id)
    if not result:
        raise HTTPException(404, "Notice not found")
    return result


# ═══════════════════════════════════════════════════════════════════
# TOGGLE ACTIVE (enable / disable)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{notice_id}/toggle", response_model=NoticeOut)
def toggle_active(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _, level, _ = _actor(current_user)
    _require_admin(level)
    result = notice_crud.toggle_active(db, notice_id)
    if not result:
        raise HTTPException(404, "Notice not found")
    return result


# ═══════════════════════════════════════════════════════════════════
# ACKNOWLEDGE  (any employee)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{notice_id}/acknowledge", response_model=AcknowledgeOut)
def acknowledge_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    actor_id, _, _ = _actor(current_user)
    try:
        return notice_crud.acknowledge_notice(db, notice_id, actor_id)
    except ValueError as e:
        raise HTTPException(400, str(e))