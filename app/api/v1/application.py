"""
app/routers/application_router.py

Endpoints for the Application module (Leave / Travel / Reimbursement).

Auth
────
  All endpoints read the JWT from the Authorization header.
  The dependency `get_current_user` must return a dict / object with:
    {
      "id":            int   ← Employee.id
      "level":         int   ← role level (1–9)
      "department_id": int | None
    }

  If your project uses a different JWT dependency, swap it in the
  `Depends(...)` calls below.

Approval flow
─────────────
  POST /applications/              → employee submits
  POST /applications/{id}/hod      → HOD approves/rejects (level 6)
  POST /applications/{id}/hr       → HR/CEO/Admin final (level 1–4)
  PATCH /applications/{id}         → employee edits own pending
  DELETE /applications/{id}        → employee withdraws / HR removes

Query / view
────────────
  GET  /applications/              → list (scoped by role)
  GET  /applications/stats         → counts by status
  GET  /applications/{id}          → single detail

Hierarchy-scoping summary
──────────────────────────
  Level 1–4 (Super Admin / CEO / HR):
    • See ALL applications across all departments
    • Can perform final HR action on Pending + HOD_Approved
    • Can hard-filter by department_id or employee_id

  Level 6 (HOD / Dept Head):
    • See applications from their own department only
    • Can perform HOD action on Pending applications from their dept
    • Cannot action their own application

  Level ≥ 7 (regular employee / intern / lead):
    • See only their own applications
    • Can create, edit (pending only), withdraw (pending only)
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user   # ← swap if your project uses a different dep
from app.crud import application as app_crud
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    HODActionIn,
    HRActionIn,
    ApplicationOut,
    ApplicationListItem,
    ApplicationStats,
    ApplicationTypeEnum,
    ApplicationStatusEnum,
)


router = APIRouter()


# ─── Helper ──────────────────────────────────────────────────────
def _actor(current_user) -> tuple[int, int, Optional[int]]:
    """
    Extract (id, level, department_id) from either:
    - a dict-like JWT payload
    - an Employee ORM object returned by get_current_user
    """
    if isinstance(current_user, dict):
        return (
            int(current_user["id"]),
            int(current_user.get("level", 99)),
            current_user.get("department_id"),
        )

    role = getattr(current_user, "role", None)
    level = getattr(role, "level", 99)

    return (
        int(getattr(current_user, "id")),
        int(level),
        getattr(current_user, "department_id", None),
    )


# ═══════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════

@router.get("/stats", response_model=ApplicationStats)
def get_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Application counts by status, scoped to the caller's visibility.

    HR / CEO / Super Admin → organisation-wide
    HOD                    → their department
    Employee               → their own
    """
    actor_id, actor_level, actor_dept_id = _actor(current_user)
    return app_crud.get_application_stats(
        db            = db,
        actor_id      = actor_id,
        actor_level   = actor_level,
        actor_dept_id = actor_dept_id,
    )


# ═══════════════════════════════════════════════════════════════════
# LIST
# ═══════════════════════════════════════════════════════════════════

@router.get("/", response_model=List[ApplicationListItem])
def list_applications(
    status:        Optional[str] = Query(None, description="Pending | HOD_Approved | HOD_Rejected | Approved | Rejected"),
    type:          Optional[str] = Query(None, description="Leave | Travel | Reimbursement"),
    department_id: Optional[int] = Query(None, description="HR only — filter to one dept"),
    employee_id:   Optional[int] = Query(None, description="HR only — filter to one employee (Employee.id)"),
    skip:          int           = Query(0, ge=0),
    limit:         int           = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    List applications visible to the caller.

    Results are enriched with employee_name, department_name, and
    actioner names so the frontend table has everything it needs
    without extra requests.
    """
    actor_id, actor_level, actor_dept_id = _actor(current_user)

    return app_crud.list_applications(
        db            = db,
        actor_id      = actor_id,
        actor_level   = actor_level,
        actor_dept_id = actor_dept_id,
        status_filter = status,
        type_filter   = type,
        department_id = department_id,
        employee_id   = employee_id,
        skip          = skip,
        limit         = limit,
    )


# ═══════════════════════════════════════════════════════════════════
# GET SINGLE
# ═══════════════════════════════════════════════════════════════════

@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Full detail for one application.
    Returns 403 if the caller does not have visibility rights.
    """
    actor_id, actor_level, actor_dept_id = _actor(current_user)

    app = app_crud.get_application_for_actor(
        db             = db,
        application_id = application_id,
        actor_id       = actor_id,
        actor_level    = actor_level,
        actor_dept_id  = actor_dept_id,
    )
    if app is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = "Application not found or access denied",
        )
    return app


# ═══════════════════════════════════════════════════════════════════
# CREATE
# ═══════════════════════════════════════════════════════════════════

@router.post("/", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create_application(
    data: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Submit a new application.
    employee_id is taken from the JWT — not the request body.
    """
    actor_id, _, _ = _actor(current_user)
    try:
        app = app_crud.create_application(db=db, data=data, employee_id=actor_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return app


# ═══════════════════════════════════════════════════════════════════
# HOD ACTION  (level 6 only)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{application_id}/hod", response_model=ApplicationOut)
def hod_action(
    application_id: int,
    data: HODActionIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Head of Department first-level review.

    • Application must be Pending.
    • Caller must be level 6 (HOD).
    • Applicant must be in the HOD's department.
    • HOD cannot action their own application.

    approve → HOD_Approved (enters HR inbox)
    reject  → HOD_Rejected (terminal)
    """
    actor_id, actor_level, actor_dept_id = _actor(current_user)

    if actor_level != 6:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Only Department Heads (level 6) can perform HOD actions",
        )
    if actor_dept_id is None:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Your account has no department assigned",
        )

    try:
        app = app_crud.hod_action(
            db             = db,
            application_id = application_id,
            actor_id       = actor_id,
            actor_dept_id  = actor_dept_id,
            data           = data,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,    detail=str(e))
    except ValueError    as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,   detail=str(e))

    return app


# ═══════════════════════════════════════════════════════════════════
# HR / FINAL ACTION  (level 1–4)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{application_id}/hr", response_model=ApplicationOut)
def hr_action(
    application_id: int,
    data: HRActionIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    HR / CEO / Super Admin final decision.

    • Caller must be level 1, 2, 3, or 4.
    • Application must be Pending (no HOD exists) or HOD_Approved.
    • HOD_Rejected applications cannot be reversed here.

    approve → Approved  (terminal ✓)
    reject  → Rejected  (terminal ✗)
    """
    actor_id, actor_level, _ = _actor(current_user)

    if actor_level not in (1, 2, 3, 4):
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Only HR, CEO, or Super Admin can perform final actions",
        )

    try:
        app = app_crud.hr_action(
            db             = db,
            application_id = application_id,
            actor_id       = actor_id,
            actor_level    = actor_level,
            data           = data,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,  detail=str(e))
    except ValueError    as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return app


# ═══════════════════════════════════════════════════════════════════
# EDIT (employee edits own pending application)
# ═══════════════════════════════════════════════════════════════════

@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: int,
    data: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Edit your own application — only while it is Pending.
    Once the HOD or HR has acted, the application is locked.
    """
    actor_id, _, _ = _actor(current_user)

    try:
        app = app_crud.update_application(
            db             = db,
            application_id = application_id,
            employee_id    = actor_id,
            data           = data,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,  detail=str(e))
    except ValueError    as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return app


# ═══════════════════════════════════════════════════════════════════
# DELETE / WITHDRAW
# ═══════════════════════════════════════════════════════════════════

@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Soft-delete an application.

    Employee: own + Pending only (withdrawal)
    HR / Admin: any application
    """
    actor_id, actor_level, _ = _actor(current_user)

    try:
        deleted = app_crud.delete_application(
            db             = db,
            application_id = application_id,
            actor_id       = actor_id,
            actor_level    = actor_level,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,  detail=str(e))
    except ValueError    as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not deleted:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = "Application not found",
        )
    return None
