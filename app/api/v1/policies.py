"""
app/routers/policy_router.py  — UPDATED

New endpoints
─────────────
  POST /policies/{id}/submit-review  → PolicyOut
      HR / HR Admin submits Draft → Review.
      Requires level 3 or 4.

  POST /policies/{id}/approve        → PolicyOut
      CEO / Super Admin marks the Review policy as approved.
      Requires level 1 or 2.
      Does NOT publish automatically.

  POST /policies/{id}/reject         → PolicyOut
      CEO / Super Admin sends policy back to Draft with a note.
      Requires level 1 or 2.

  POST /policies/{id}/publish        → PolicyOut
      HR / HR Admin publishes an approved Review policy → Active.
      Requires level 3 or 4 AND policy.approved_by must be set.

  GET  /policies/my                  → List[EmployeePolicyItem]
      Employee-facing list with acknowledged=True/False per policy.
      Audience-scoped, Active only.

Updated:
  GET /policies/stats  → includes pending_approval count
  GET /policies/       → admins see all; employees see my policies via /my

Workflow summary
────────────────
  HR creates Draft  →  HR submits for review  →  CEO approves (or rejects)
  →  HR publishes (Active)  →  Employees see & acknowledge

Auth levels
───────────
  level 1–2 (Super Admin, CEO): approve / reject
  level 3–4 (HR Admin, HR):     create, edit, submit, publish, delete, pin
  level ≥ 5 (employees):        view Active, acknowledge, /my list
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.crud import policies as policy_crud
from app.schemas.policies import (
    PolicyCreate, PolicyUpdate,
    PolicyOut, PolicyListItem,
    PolicyStats, AcknowledgeOut,
    PolicySubmitReview, PolicyApprove,
    EmployeePolicyItem,
)

router = APIRouter()


# ─── Auth helpers ────────────────────────────────────────────────

def _actor(current_user):
    """Return (employee_id, level, role_obj) from the user object returned by get_current_user."""
    role  = getattr(current_user, "role", None)
    level = getattr(role, "level", 99) if role else 99
    return (
        int(getattr(current_user, "id")),
        int(level),
        role,
    )


def _blank_to_none(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _parse_optional_bool(value: Optional[str]) -> Optional[bool]:
    value = _blank_to_none(value)
    if value is None:
        return None
    if value.lower() in {"true", "1", "yes"}:
        return True
    if value.lower() in {"false", "0", "no"}:
        return False
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="mandatory must be a boolean value",
    )


def _require_hr(level: int):
    """Levels 1–4 can manage policies (create/edit/delete/pin/submit/publish)."""
    if level not in (1, 2, 3, 4):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HR Admin or above required",
        )


def _require_ceo(level: int):
    """Only levels 1–2 (Super Admin / CEO) can approve/reject."""
    if level not in (1, 2):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CEO or Super Admin required to approve/reject policies",
        )


def _require_hr_only(level: int):
    """Levels 3–4 (HR Admin / HR) for submit/publish.
    CEOs don't submit their own policies for their own approval."""
    if level not in (1, 2, 3, 4):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HR Admin or above required",
        )


def _get_employee_context(db: Session, employee_id: int):
    try:
        from app.models.employee import Employee
        from app.models.department import Department
        from app.models.role import Role

        emp = db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.is_deleted == False,
        ).first()
        if not emp:
            return None, None

        dept_name, role_name = None, None
        if emp.department_id:
            dept = db.query(Department).filter(Department.id == emp.department_id).first()
            dept_name = dept.department if dept else None
        if emp.role_id:
            role = db.query(Role).filter(Role.id == emp.role_id).first()
            role_name = role.name if role else None

        return dept_name, role_name
    except Exception:
        return None, None


# ═══════════════════════════════════════════════════════════════════
# STATS  (must be above /{id})
# ═══════════════════════════════════════════════════════════════════

@router.get("/stats", response_model=PolicyStats)
def get_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _, level, _ = _actor(current_user)
    _require_hr(level)
    return policy_crud.get_policy_stats(db)


# ═══════════════════════════════════════════════════════════════════
# MY POLICIES  — employee view with ack status (above /{id})
# ═══════════════════════════════════════════════════════════════════

@router.get("/my", response_model=List[EmployeePolicyItem])
def my_policies(
    category:  Optional[str] = Query(None),
    mandatory: Optional[str] = Query(None),
    search:    Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Employee-facing policy list.
    Returns only Active policies the employee's audience can see,
    annotated with acknowledged=True/False for THIS employee.
    """
    actor_id, _, _ = _actor(current_user)
    dept_name, role_name = _get_employee_context(db, actor_id)
    mandatory_val = _parse_optional_bool(mandatory)

    return policy_crud.get_my_policies(
        db          = db,
        employee_id = actor_id,
        dept_name   = dept_name,
        role_name   = role_name,
        search      = _blank_to_none(search),
        mandatory   = mandatory_val,
        category    = _blank_to_none(category),
    )


@router.get("/my/acked", response_model=List[int])
def my_acked_policies(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    actor_id, _, _ = _actor(current_user)
    return policy_crud.get_employee_acks(db, actor_id)


# ═══════════════════════════════════════════════════════════════════
# LIST  (admin view)
# ═══════════════════════════════════════════════════════════════════

@router.get("/", response_model=List[PolicyListItem])
def list_policies(
    category:  Optional[str] = Query(None),
    status:    Optional[str] = Query(None),
    audience:  Optional[str] = Query(None),
    mandatory: Optional[str] = Query(None),
    search:    Optional[str] = Query(None),
    skip:      int           = Query(0, ge=0),
    limit:     int           = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    actor_id, actor_level, _ = _actor(current_user)
    is_admin = actor_level in (1, 2, 3, 4)
    mandatory_value = _parse_optional_bool(mandatory)

    dept_name, role_name = None, None
    if not is_admin:
        dept_name, role_name = _get_employee_context(db, actor_id)

    return policy_crud.list_policies(
        db                  = db,
        is_admin            = is_admin,
        employee_id         = actor_id,
        employee_dept_name  = dept_name,
        employee_role_name  = role_name,
        category            = _blank_to_none(category),
        status              = _blank_to_none(status) if is_admin else None,
        audience            = _blank_to_none(audience) if is_admin else None,
        mandatory           = mandatory_value,
        search              = _blank_to_none(search),
        skip                = skip,
        limit               = limit,
    )


# ═══════════════════════════════════════════════════════════════════
# GET SINGLE
# ═══════════════════════════════════════════════════════════════════

@router.get("/{policy_id}", response_model=PolicyOut)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    actor_id, actor_level, _ = _actor(current_user)
    is_admin = actor_level in (1, 2, 3, 4)

    result = policy_crud.get_policy_detail(db, policy_id)
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")

    if not is_admin and result.status != "Active":
        raise HTTPException(status_code=403, detail="This policy is not currently available")

    return result


# ═══════════════════════════════════════════════════════════════════
# CREATE  (HR / Admin)
# ═══════════════════════════════════════════════════════════════════

@router.post("/", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(
    data: PolicyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    actor_id, actor_level, _ = _actor(current_user)
    _require_hr(actor_level)
    return policy_crud.create_policy(db, data, created_by=actor_id)


# ═══════════════════════════════════════════════════════════════════
# UPDATE  (HR / Admin)
# ═══════════════════════════════════════════════════════════════════

@router.patch("/{policy_id}", response_model=PolicyOut)
def update_policy(
    policy_id: int,
    data: PolicyUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _, actor_level, _ = _actor(current_user)
    _require_hr(actor_level)
    result = policy_crud.update_policy(db, policy_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result


# ═══════════════════════════════════════════════════════════════════
# DELETE  (HR / Admin)
# ═══════════════════════════════════════════════════════════════════

@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _, actor_level, _ = _actor(current_user)
    _require_hr(actor_level)
    if not policy_crud.delete_policy(db, policy_id):
        raise HTTPException(status_code=404, detail="Policy not found")
    return None


# ═══════════════════════════════════════════════════════════════════
# PIN TOGGLE  (HR / Admin)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{policy_id}/pin", response_model=PolicyOut)
def toggle_pin(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _, actor_level, _ = _actor(current_user)
    _require_hr(actor_level)
    result = policy_crud.toggle_pin(db, policy_id)
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result


# ═══════════════════════════════════════════════════════════════════
# STATUS TOGGLE (Active ↔ Archived)  (HR / Admin)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{policy_id}/toggle-status", response_model=PolicyOut)
def toggle_status(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _, actor_level, _ = _actor(current_user)
    _require_hr(actor_level)
    result = policy_crud.toggle_status(db, policy_id)
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result


# ═══════════════════════════════════════════════════════════════════
# SUBMIT FOR REVIEW  (HR / HR Admin → CEO)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{policy_id}/submit-review", response_model=PolicyOut)
def submit_for_review(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    HR submits a Draft policy for CEO review.
    Transitions: Draft → Review
    """
    _, actor_level, _ = _actor(current_user)
    _require_hr_only(actor_level)

    try:
        result = policy_crud.submit_for_review(db, policy_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result


# ═══════════════════════════════════════════════════════════════════
# APPROVE  (CEO / Super Admin only)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{policy_id}/approve", response_model=PolicyOut)
def approve_policy(
    policy_id: int,
    body: PolicyApprove = PolicyApprove(),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    CEO approves a Review policy.
    Policy remains in Review status; HR must separately publish it.
    """
    actor_id, actor_level, _ = _actor(current_user)
    _require_ceo(actor_level)

    try:
        result = policy_crud.approve_policy(db, policy_id, actor_id, note=body.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result


# ═══════════════════════════════════════════════════════════════════
# REJECT  (CEO / Super Admin only)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{policy_id}/reject", response_model=PolicyOut)
def reject_policy(
    policy_id: int,
    body: PolicyApprove = PolicyApprove(),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    CEO sends a Review policy back to Draft with a rejection note.
    """
    actor_id, actor_level, _ = _actor(current_user)
    _require_ceo(actor_level)

    try:
        result = policy_crud.reject_policy(db, policy_id, note=body.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result


# ═══════════════════════════════════════════════════════════════════
# PUBLISH  (HR / HR Admin — only if CEO already approved)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{policy_id}/publish", response_model=PolicyOut)
def publish_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    HR publishes a CEO-approved policy: Review (approved) → Active.
    Will fail with 400 if CEO has not yet approved.
    """
    _, actor_level, _ = _actor(current_user)
    _require_hr_only(actor_level)

    try:
        result = policy_crud.publish_policy(db, policy_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    return result


# ═══════════════════════════════════════════════════════════════════
# ACKNOWLEDGE  (any employee)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{policy_id}/acknowledge", response_model=AcknowledgeOut)
def acknowledge_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    actor_id, _, _ = _actor(current_user)
    try:
        return policy_crud.acknowledge_policy(db, policy_id, actor_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))