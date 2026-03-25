"""
app/crud/application.py

Business logic for the Application module.

Approval hierarchy
══════════════════
  Employee / Intern / Lead  →  submits (status = Pending)
  HOD (dept head)           →  first review
                                 approve → HOD_Approved  (goes to HR inbox)
                                 reject  → HOD_Rejected  (terminal)
  HR / Super Admin / CEO    →  final review
                                 approve → Approved      (terminal)
                                 reject  → Rejected      (terminal)

Role levels used throughout
══════════════════════════════
  1 = Super Admin   seesAll + full action
  2 = CEO           seesAll + full action (same as HR for this module)
  3 = HR Admin      seesAll + full action
  4 = HR Officer    seesAll + full action
  6 = Dept Head     sees own dept only + HOD action
  ≥7 = Employee     sees own applications only
"""

from datetime import datetime
from typing import List, Optional, Dict

from sqlalchemy.orm import Session, joinedload

from app.models.application import Application, ApplicationStatusEnum, ApplicationTypeEnum
from app.models.employee import Employee
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    HODActionIn,
    HRActionIn,
    ApplicationListItem,
    ApplicationStats,
)


# ═══════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════

def _get_employee(db: Session, employee_id: int) -> Optional[Employee]:
    return db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.is_deleted == False,
    ).first()


def _can_act_on(actor_level: int, target_level: int) -> bool:
    return actor_level < target_level


def _employee_level(emp: Optional[Employee]) -> int:
    if emp is None or emp.role is None or emp.role.level is None:
        return 99
    return int(emp.role.level)


def _get_dept_head_id(db: Session, department_id: Optional[int]) -> Optional[int]:
    """
    Return the Employee.id of the head of the given department.
    Looks up Department.head_id.
    Returns None if department has no head assigned.
    """
    if department_id is None:
        return None
    try:
        from app.models.department import Department
        dept = db.query(Department).filter(Department.id == department_id).first()
        return dept.head_id if dept else None
    except Exception:
        return None


def _is_hr_role(level: int) -> bool:
    """Levels that act as HR (final approver)."""
    return level in (1, 2, 3, 4)


def _is_hod_role(level: int) -> bool:
    """Level 6 = Department Head."""
    return level == 6


def _employee_name(emp: Optional[Employee]) -> Optional[str]:
    if emp is None:
        return None
    return f"{emp.f_name} {emp.l_name}".strip()


def _build_list_item(app: Application, emp_map: Dict[int, Employee]) -> ApplicationListItem:
    """
    Assemble ApplicationListItem from an ORM Application row +
    a pre-loaded employee map  { employee_id: Employee }.
    """
    emp      = emp_map.get(app.employee_id)
    hod_emp  = emp_map.get(app.hod_action_by) if app.hod_action_by else None
    hr_emp   = emp_map.get(app.hr_action_by)  if app.hr_action_by  else None

    # Department name via the employee's relationship
    dept_name = None
    if emp and emp.department:
        dept_name = emp.department.department

    return ApplicationListItem(
        id              = app.id,
        employee_id     = app.employee_id,
        employee_name   = _employee_name(emp),
        department_name = dept_name,
        employee_image  = emp.image if emp else None,
        type            = app.type,
        status          = app.status,
        from_date       = app.from_date,
        to_date         = app.to_date,
        reason          = app.reason,
        amount          = app.amount,
        destination     = app.destination,
        hod_rejection_reason = app.hod_rejection_reason,
        hr_rejection_reason  = app.hr_rejection_reason,
        hod_actioner_name    = _employee_name(hod_emp),
        hr_actioner_name     = _employee_name(hr_emp),
        created_at      = app.created_at,
    )


# ═══════════════════════════════════════════════════════════════════
# CREATE
# ═══════════════════════════════════════════════════════════════════

def create_application(
    db: Session,
    data: ApplicationCreate,
    employee_id: int,           # Employee.id from JWT
) -> Application:
    """
    Create a new application.  Status always starts as Pending.
    """
    emp = _get_employee(db, employee_id)
    if emp is None:
        raise ValueError("Employee not found")

    obj = Application(
        employee_id = employee_id,
        type        = data.type,
        from_date   = data.from_date,
        to_date     = data.to_date,
        reason      = data.reason,
        amount      = data.amount,
        destination = data.destination,
        extra_data  = data.extra_data,
        status      = ApplicationStatusEnum.pending,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ═══════════════════════════════════════════════════════════════════
# READ — single application
# ═══════════════════════════════════════════════════════════════════

def get_application_by_id(db: Session, application_id: int) -> Optional[Application]:
    return (
        db.query(Application)
        .options(
            joinedload(Application.employee),
            joinedload(Application.hod_actioner),
            joinedload(Application.hr_actioner),
        )
        .filter(
            Application.id         == application_id,
            Application.is_deleted == False,
        )
        .first()
    )


def get_application_for_actor(
    db: Session,
    application_id: int,
    actor_id: int,
    actor_level: int,
    actor_dept_id: Optional[int] = None,
) -> Optional[Application]:
    """
    Load an application and verify the actor is allowed to see it.
    Returns None if not found or not authorized.
    """
    app = get_application_by_id(db, application_id)
    if app is None:
        return None

    # Own application
    if app.employee_id == actor_id:
        return app

    # HR / CEO / Super Admin see everything
    if _is_hr_role(actor_level):
        return app

    # HOD sees their own dept
    if _is_hod_role(actor_level) and actor_dept_id:
        emp = _get_employee(db, app.employee_id)
        if emp and emp.department_id == actor_dept_id:
            return app

    return None


# ═══════════════════════════════════════════════════════════════════
# READ — list with scoping and enrichment
# ═══════════════════════════════════════════════════════════════════

def list_applications(
    db: Session,
    actor_id: int,
    actor_level: int,
    actor_dept_id: Optional[int] = None,
    # Filters
    status_filter:    Optional[str] = None,
    type_filter:      Optional[str] = None,
    department_id:    Optional[int] = None,
    employee_id:      Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[ApplicationListItem]:
    """
    Return applications visible to the actor, enriched with employee metadata.

    Scoping rules:
      HR / CEO / Super Admin  →  ALL applications
      HOD (level 6)           →  applications from employees in their dept
      Employee (level ≥ 7)    →  only their own applications
    """
    q = (
        db.query(Application)
        .filter(Application.is_deleted == False)
        .order_by(Application.created_at.desc())
    )

    # ── Scope ───────────────────────────────────────────────────
    if _is_hr_role(actor_level):
        # Full org visibility — optionally scope to one dept
        if department_id is not None:
            q = q.join(Employee, Application.employee_id == Employee.id).filter(
                Employee.department_id == department_id,
                Employee.is_deleted    == False,
            )
    elif _is_hod_role(actor_level):
        # Only applications from employees in the HOD's department
        dept_id = actor_dept_id
        if dept_id is None:
            return []  # HOD with no dept → see nothing
        q = q.join(Employee, Application.employee_id == Employee.id).filter(
            Employee.department_id == dept_id,
            Employee.is_deleted    == False,
        )
        # HOD inbox: Pending + HOD_Approved (for awareness) + their own decisions
        # We do NOT restrict by status here — they can see the full history of their dept
    else:
        # Regular employee: own applications only
        q = q.filter(Application.employee_id == actor_id)

    # ── Explicit filters ─────────────────────────────────────────
    if status_filter:
        q = q.filter(Application.status == status_filter)

    if type_filter:
        q = q.filter(Application.type == type_filter)

    if employee_id is not None and _is_hr_role(actor_level):
        # HR can filter to one employee
        q = q.filter(Application.employee_id == employee_id)

    apps = q.offset(skip).limit(limit).all()
    if not apps:
        return []

    # ── Enrich with employee metadata ────────────────────────────
    # Collect all employee IDs needed (applicants + actioners)
    emp_ids = set()
    for app in apps:
        emp_ids.add(app.employee_id)
        if app.hod_action_by:
            emp_ids.add(app.hod_action_by)
        if app.hr_action_by:
            emp_ids.add(app.hr_action_by)

    employees = (
        db.query(Employee)
        .options(joinedload(Employee.department))
        .filter(Employee.id.in_(emp_ids))
        .all()
    )
    emp_map = {e.id: e for e in employees}

    return [_build_list_item(app, emp_map) for app in apps]


# ═══════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════

def get_application_stats(
    db: Session,
    actor_id: int,
    actor_level: int,
    actor_dept_id: Optional[int] = None,
) -> ApplicationStats:
    """Count applications by status, respecting the same scoping rules."""
    q = db.query(Application).filter(Application.is_deleted == False)

    if _is_hr_role(actor_level):
        pass  # all
    elif _is_hod_role(actor_level) and actor_dept_id:
        q = q.join(Employee, Application.employee_id == Employee.id).filter(
            Employee.department_id == actor_dept_id,
            Employee.is_deleted    == False,
        )
    else:
        q = q.filter(Application.employee_id == actor_id)

    apps = q.all()

    counts = {s.value: 0 for s in ApplicationStatusEnum}
    for app in apps:
        counts[app.status.value] += 1

    return ApplicationStats(
        total        = len(apps),
        pending      = counts[ApplicationStatusEnum.pending.value],
        hod_approved = counts[ApplicationStatusEnum.hod_approved.value],
        hod_rejected = counts[ApplicationStatusEnum.hod_rejected.value],
        approved     = counts[ApplicationStatusEnum.approved.value],
        rejected     = counts[ApplicationStatusEnum.rejected.value],
    )


# ═══════════════════════════════════════════════════════════════════
# HOD ACTION
# ═══════════════════════════════════════════════════════════════════

def hod_action(
    db: Session,
    application_id: int,
    actor_id: int,           # the HOD's Employee.id
    actor_dept_id: int,      # the HOD's department_id
    data: HODActionIn,
) -> Application:
    """
    HOD first-level review.

    Rules:
      • Application must be in Pending status.
      • The applicant must be in the HOD's department.
      • HOD cannot action their own application.
      • HOD can only action lower-power roles.

    After approve → HOD_Approved (HR inbox)
    After reject  → HOD_Rejected (terminal)
    """
    app = get_application_by_id(db, application_id)

    if app is None:
        raise ValueError("Application not found")

    if app.employee_id == actor_id:
        raise PermissionError("HODs cannot action their own applications")

    if app.status != ApplicationStatusEnum.pending:
        raise ValueError(
            f"Application is already '{app.status.value}' — only Pending applications can be reviewed by HOD"
        )

    # Verify the applicant is in the HOD's dept
    emp = _get_employee(db, app.employee_id)
    if emp is None or emp.department_id != actor_dept_id:
        raise PermissionError("This application is not from your department")

    if not _can_act_on(6, _employee_level(emp)):
        raise PermissionError("You can only action applications from lower-power roles")

    now = datetime.utcnow()

    if data.action == "approve":
        app.status       = ApplicationStatusEnum.hod_approved
        app.hod_action_by = actor_id
        app.hod_action_at = now
    else:
        app.status               = ApplicationStatusEnum.hod_rejected
        app.hod_action_by        = actor_id
        app.hod_action_at        = now
        app.hod_rejection_reason = data.rejection_reason

    db.commit()
    db.refresh(app)
    return app


# ═══════════════════════════════════════════════════════════════════
# HR ACTION (final)
# ═══════════════════════════════════════════════════════════════════

def hr_action(
    db: Session,
    application_id: int,
    actor_id: int,           # HR employee's Employee.id
    actor_level: int,
    data: HRActionIn,
) -> Application:
    """
    HR / CEO / Super Admin final decision.

    Rules:
      • Actor must be HR-role (level 1–4).
      • Actor must outrank the applicant.
      • Application must be in Pending or HOD_Approved.
      • HR cannot approve/reject HOD_Rejected applications.

    After approve → Approved  (terminal)
    After reject  → Rejected  (terminal)
    """
    if not _is_hr_role(actor_level):
        raise PermissionError("Only HR, CEO, or Super Admin can perform this action")

    app = get_application_by_id(db, application_id)

    if app is None:
        raise ValueError("Application not found")

    applicant = _get_employee(db, app.employee_id)
    if applicant is None:
        raise ValueError("Applicant not found")

    if app.employee_id == actor_id:
        raise PermissionError("You cannot action your own application")

    if not _can_act_on(actor_level, _employee_level(applicant)):
        raise PermissionError("You can only action applications from lower-power roles")

    actionable = {ApplicationStatusEnum.pending, ApplicationStatusEnum.hod_approved}
    if app.status not in actionable:
        raise ValueError(
            f"Application is '{app.status.value}' — HR can only action Pending or HOD_Approved applications"
        )

    now = datetime.utcnow()

    if data.action == "approve":
        app.status       = ApplicationStatusEnum.approved
        app.hr_action_by = actor_id
        app.hr_action_at = now
    else:
        app.status              = ApplicationStatusEnum.rejected
        app.hr_action_by        = actor_id
        app.hr_action_at        = now
        app.hr_rejection_reason = data.rejection_reason

    db.commit()
    db.refresh(app)
    return app


# ═══════════════════════════════════════════════════════════════════
# EMPLOYEE UPDATE (edit own pending application)
# ═══════════════════════════════════════════════════════════════════

def update_application(
    db: Session,
    application_id: int,
    employee_id: int,
    data: ApplicationUpdate,
) -> Application:
    """
    Employee may edit their own application only while it is Pending.
    Once HOD or HR has acted, editing is locked.
    """
    app = db.query(Application).filter(
        Application.id         == application_id,
        Application.is_deleted == False,
    ).first()

    if app is None:
        raise ValueError("Application not found")

    if app.employee_id != employee_id:
        raise PermissionError("You can only edit your own applications")

    if app.status != ApplicationStatusEnum.pending:
        raise ValueError("Only Pending applications can be edited")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(app, field, value)

    db.commit()
    db.refresh(app)
    return app


# ═══════════════════════════════════════════════════════════════════
# DELETE (soft) — employee withdraws, or HR removes
# ═══════════════════════════════════════════════════════════════════

def delete_application(
    db: Session,
    application_id: int,
    actor_id: int,
    actor_level: int,
) -> bool:
    """
    Soft-delete an application.

    Employee:  only their own, only while Pending
    HR / Admin: any application
    """
    app = db.query(Application).filter(
        Application.id         == application_id,
        Application.is_deleted == False,
    ).first()

    if app is None:
        return False

    if not _is_hr_role(actor_level):
        # Regular employee / HOD: own + pending only
        if app.employee_id != actor_id:
            raise PermissionError("You can only delete your own applications")
        if app.status != ApplicationStatusEnum.pending:
            raise ValueError("Only Pending applications can be withdrawn")

    app.is_deleted = True
    db.commit()
    return True
