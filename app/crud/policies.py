"""
app/crud/policy.py  — UPDATED

New CRUD functions:
  submit_for_review(db, policy_id, submitted_by)
      Draft  → Review  (HR / HR Admin only; validated in router)
      Sets submitted_for_review_at = now()

  approve_policy(db, policy_id, approver_id, note)
      Review → stays in Review but marks approved_by / approved_at
      CEO approval does NOT automatically publish; HR must call /publish.
      Raises ValueError if policy not in Review status.

  publish_policy(db, policy_id)
      Review (approved) → Active
      Raises ValueError if approved_by is None (not yet approved).

  get_my_policies(db, employee_id, dept_name, role_name)
      Returns EmployeePolicyItem list with acknowledged=True/False
      for the requesting employee.

Updated helpers:
  _to_list_item / _to_out — include approval fields
  get_policy_stats         — includes pending_approval count
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.policy import Policy, PolicyAcknowledgement, PolicyStatusEnum
from app.schemas.policies import (
    PolicyCreate, PolicyUpdate,
    PolicyListItem, PolicyOut,
    PolicyStats, AcknowledgeOut,
    EmployeePolicyItem,
)


# ═══════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════

def _ack_count(db: Session, policy_id: int) -> int:
    return db.query(func.count(PolicyAcknowledgement.id)).filter(
        PolicyAcknowledgement.policy_id == policy_id
    ).scalar() or 0


def _total_recipients(db: Session, audience: str) -> int:
    try:
        from app.models.employee import Employee
        from app.models.department import Department
        from app.models.role import Role

        base_q = db.query(func.count(Employee.id)).filter(
            Employee.is_deleted == False,
            Employee.employment_status == "active",
        )

        if audience == "All Employees":
            return base_q.scalar() or 0

        dept_count = (
            base_q
            .join(Department, Employee.department_id == Department.id)
            .filter(Department.department == audience)
            .scalar() or 0
        )
        if dept_count:
            return dept_count

        role_count = (
            base_q
            .join(Role, Employee.role_id == Role.id)
            .filter(Role.name == audience)
            .scalar() or 0
        )
        return role_count
    except Exception:
        return 0


def _employee_full_name(employee) -> Optional[str]:
    if employee:
        return f"{employee.f_name} {employee.l_name}".strip()
    return None


def _to_list_item(db: Session, policy: Policy) -> PolicyListItem:
    return PolicyListItem(
        id               = policy.id,
        title            = policy.title,
        category         = policy.category.value,
        status           = policy.status.value,
        audience         = policy.audience,
        version          = policy.version,
        mandatory        = policy.mandatory,
        pinned           = policy.pinned,
        summary          = policy.summary,
        created_by       = policy.created_by,
        created_by_name  = _employee_full_name(policy.author),
        created_at       = policy.created_at,
        updated_at       = policy.updated_at,
        ack_count        = _ack_count(db, policy.id),
        total_recipients = _total_recipients(db, policy.audience),
        # approval
        approved_by      = policy.approved_by,
        approved_by_name = _employee_full_name(policy.approver),
        approved_at      = policy.approved_at,
        approval_note    = policy.approval_note,
        submitted_for_review_at = policy.submitted_for_review_at,
    )


def _to_out(db: Session, policy: Policy) -> PolicyOut:
    return PolicyOut(
        id               = policy.id,
        title            = policy.title,
        category         = policy.category.value,
        status           = policy.status.value,
        audience         = policy.audience,
        version          = policy.version,
        mandatory        = policy.mandatory,
        pinned           = policy.pinned,
        summary          = policy.summary,
        content          = policy.content,
        created_by       = policy.created_by,
        created_by_name  = _employee_full_name(policy.author),
        created_at       = policy.created_at,
        updated_at       = policy.updated_at,
        ack_count        = _ack_count(db, policy.id),
        total_recipients = _total_recipients(db, policy.audience),
        extra_data       = policy.extra_data,
        # approval
        approved_by      = policy.approved_by,
        approved_by_name = _employee_full_name(policy.approver),
        approved_at      = policy.approved_at,
        approval_note    = policy.approval_note,
        submitted_for_review_at = policy.submitted_for_review_at,
    )


# ═══════════════════════════════════════════════════════════════════
# HELPERS — shared query
# ═══════════════════════════════════════════════════════════════════

def get_policy_by_id(db: Session, policy_id: int) -> Optional[Policy]:
    return (
        db.query(Policy)
        .options(joinedload(Policy.author), joinedload(Policy.approver))
        .filter(Policy.id == policy_id, Policy.is_deleted == False)
        .first()
    )


# ═══════════════════════════════════════════════════════════════════
# CREATE
# ═══════════════════════════════════════════════════════════════════

def create_policy(db: Session, data: PolicyCreate, created_by: int) -> PolicyOut:
    # HR cannot directly create an Active policy — must go through approval
    # If they try to set status=Active, demote to Draft
    status = data.status
    if status == PolicyStatusEnum.active:
        status = PolicyStatusEnum.draft

    policy = Policy(
        title      = data.title.strip(),
        summary    = data.summary.strip(),
        content    = data.content.strip(),
        version    = data.version,
        category   = data.category,
        status     = status,
        audience   = data.audience,
        mandatory  = data.mandatory,
        pinned     = data.pinned,
        extra_data = data.extra_data,
        created_by = created_by,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return _to_out(db, policy)


# ═══════════════════════════════════════════════════════════════════
# READ
# ═══════════════════════════════════════════════════════════════════

def get_policy_detail(db: Session, policy_id: int) -> Optional[PolicyOut]:
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        return None
    return _to_out(db, policy)


def list_policies(
    db: Session,
    is_admin: bool = True,
    employee_id: Optional[int] = None,
    employee_dept_name: Optional[str] = None,
    employee_role_name: Optional[str] = None,
    category:  Optional[str]  = None,
    status:    Optional[str]  = None,
    audience:  Optional[str]  = None,
    mandatory: Optional[bool] = None,
    search:    Optional[str]  = None,
    pinned_first: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> List[PolicyListItem]:
    q = (
        db.query(Policy)
        .options(joinedload(Policy.author), joinedload(Policy.approver))
        .filter(Policy.is_deleted == False)
    )

    if is_admin:
        if status:
            q = q.filter(Policy.status == status)
    else:
        q = q.filter(Policy.status == PolicyStatusEnum.active)
        if employee_dept_name or employee_role_name:
            from sqlalchemy import or_
            conditions = [Policy.audience == "All Employees"]
            if employee_dept_name:
                conditions.append(Policy.audience == employee_dept_name)
            if employee_role_name:
                conditions.append(Policy.audience == employee_role_name)
            q = q.filter(or_(*conditions))
        else:
            q = q.filter(Policy.audience == "All Employees")

    if category:
        q = q.filter(Policy.category == category)
    if audience and is_admin:
        q = q.filter(Policy.audience == audience)
    if mandatory is not None:
        q = q.filter(Policy.mandatory == mandatory)
    if search:
        term = f"%{search.lower()}%"
        q = q.filter(
            Policy.title.ilike(term) |
            Policy.summary.ilike(term) |
            Policy.audience.ilike(term)
        )

    if pinned_first:
        q = q.order_by(Policy.pinned.desc(), Policy.updated_at.desc())
    else:
        q = q.order_by(Policy.updated_at.desc())

    policies = q.offset(skip).limit(limit).all()
    return [_to_list_item(db, p) for p in policies]


# ═══════════════════════════════════════════════════════════════════
# EMPLOYEE-FACING LIST  (with ack status)
# ═══════════════════════════════════════════════════════════════════

def get_my_policies(
    db: Session,
    employee_id: int,
    dept_name: Optional[str] = None,
    role_name: Optional[str] = None,
    search: Optional[str] = None,
    mandatory: Optional[bool] = None,
    category: Optional[str] = None,
) -> List[EmployeePolicyItem]:
    """
    Returns all Active policies the employee can see,
    annotated with whether they personally acknowledged each one.
    """
    from sqlalchemy import or_

    q = (
        db.query(Policy)
        .options(joinedload(Policy.author))
        .filter(
            Policy.is_deleted == False,
            Policy.status == PolicyStatusEnum.active,
        )
    )

    # Audience scoping
    conditions = [Policy.audience == "All Employees"]
    if dept_name:
        conditions.append(Policy.audience == dept_name)
    if role_name:
        conditions.append(Policy.audience == role_name)
    q = q.filter(or_(*conditions))

    if category:
        q = q.filter(Policy.category == category)
    if mandatory is not None:
        q = q.filter(Policy.mandatory == mandatory)
    if search:
        term = f"%{search.lower()}%"
        q = q.filter(Policy.title.ilike(term) | Policy.summary.ilike(term))

    q = q.order_by(Policy.pinned.desc(), Policy.updated_at.desc())
    policies = q.all()

    # Fetch all ack records for this employee in one query
    policy_ids = [p.id for p in policies]
    acks = {}
    if policy_ids:
        rows = (
            db.query(PolicyAcknowledgement)
            .filter(
                PolicyAcknowledgement.employee_id == employee_id,
                PolicyAcknowledgement.policy_id.in_(policy_ids),
            )
            .all()
        )
        acks = {r.policy_id: r.acked_at for r in rows}

    result = []
    for p in policies:
        result.append(EmployeePolicyItem(
            id               = p.id,
            title            = p.title,
            category         = p.category.value,
            status           = p.status.value,
            audience         = p.audience,
            version          = p.version,
            mandatory        = p.mandatory,
            pinned           = p.pinned,
            summary          = p.summary,
            created_at       = p.created_at,
            updated_at       = p.updated_at,
            ack_count        = _ack_count(db, p.id),
            total_recipients = _total_recipients(db, p.audience),
            acknowledged     = p.id in acks,
            acked_at         = acks.get(p.id),
        ))
    return result


# ═══════════════════════════════════════════════════════════════════
# UPDATE
# ═══════════════════════════════════════════════════════════════════

def update_policy(db: Session, policy_id: int, data: PolicyUpdate) -> Optional[PolicyOut]:
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        # Prevent HR from directly setting status=Active without approval
        if field == "status" and value == PolicyStatusEnum.active:
            if not policy.approved_by:
                # silently demote to draft; router should prevent this anyway
                value = PolicyStatusEnum.draft
        setattr(policy, field, value)

    # If status changed back to Draft, clear approval
    if data.status in (PolicyStatusEnum.draft, None):
        pass  # keep approval intact unless explicitly reset

    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    return _to_out(db, policy)


# ═══════════════════════════════════════════════════════════════════
# WORKFLOW ACTIONS
# ═══════════════════════════════════════════════════════════════════

def submit_for_review(
    db: Session,
    policy_id: int,
) -> Optional[PolicyOut]:
    """
    HR / HR Admin submits a Draft policy for CEO review.
    Transitions Draft → Review.
    Raises ValueError if not in Draft status.
    """
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        return None

    if policy.status != PolicyStatusEnum.draft:
        raise ValueError(f"Only Draft policies can be submitted for review. Current status: {policy.status.value}")

    policy.status = PolicyStatusEnum.review
    policy.submitted_for_review_at = datetime.utcnow()
    policy.updated_at = datetime.utcnow()
    # Reset any previous approval if re-submitting
    policy.approved_by = None
    policy.approved_at = None
    policy.approval_note = None
    db.commit()
    db.refresh(policy)
    return _to_out(db, policy)


def approve_policy(
    db: Session,
    policy_id: int,
    approver_id: int,   # CEO employee id
    note: Optional[str] = None,
) -> Optional[PolicyOut]:
    """
    CEO approves a policy in Review status.
    Does NOT publish — HR must still call /publish.
    Raises ValueError if not in Review status.
    """
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        return None

    if policy.status != PolicyStatusEnum.review:
        raise ValueError(f"Only Review policies can be approved. Current status: {policy.status.value}")

    policy.approved_by   = approver_id
    policy.approved_at   = datetime.utcnow()
    policy.approval_note = note
    policy.updated_at    = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    return _to_out(db, policy)


def reject_policy(
    db: Session,
    policy_id: int,
    note: Optional[str] = None,
) -> Optional[PolicyOut]:
    """
    CEO sends policy back to Draft with an optional rejection note.
    """
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        return None

    if policy.status != PolicyStatusEnum.review:
        raise ValueError(f"Only Review policies can be rejected. Current status: {policy.status.value}")

    policy.status        = PolicyStatusEnum.draft
    policy.approval_note = note  # rejection reason stored here
    policy.approved_by   = None
    policy.approved_at   = None
    policy.updated_at    = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    return _to_out(db, policy)


def publish_policy(
    db: Session,
    policy_id: int,
) -> Optional[PolicyOut]:
    """
    HR publishes an approved policy (Review + approved_by set → Active).
    Raises ValueError if not approved yet.
    """
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        return None

    if policy.status != PolicyStatusEnum.review:
        raise ValueError(f"Only Review policies can be published. Current status: {policy.status.value}")

    if not policy.approved_by:
        raise ValueError("Policy must be approved by CEO before it can be published.")

    policy.status     = PolicyStatusEnum.active
    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    return _to_out(db, policy)


# ═══════════════════════════════════════════════════════════════════
# TOGGLE HELPERS
# ═══════════════════════════════════════════════════════════════════

def toggle_pin(db: Session, policy_id: int) -> Optional[PolicyOut]:
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        return None
    policy.pinned     = not policy.pinned
    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    return _to_out(db, policy)


def toggle_status(db: Session, policy_id: int) -> Optional[PolicyOut]:
    """Active ↔ Archived only."""
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        return None

    if policy.status == PolicyStatusEnum.active:
        policy.status = PolicyStatusEnum.archived
    elif policy.status == PolicyStatusEnum.archived:
        policy.status = PolicyStatusEnum.active

    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    return _to_out(db, policy)


# ═══════════════════════════════════════════════════════════════════
# DELETE (soft)
# ═══════════════════════════════════════════════════════════════════

def delete_policy(db: Session, policy_id: int) -> bool:
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        return False
    policy.is_deleted = True
    policy.updated_at = datetime.utcnow()
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════
# ACKNOWLEDGE
# ═══════════════════════════════════════════════════════════════════

def acknowledge_policy(db: Session, policy_id: int, employee_id: int) -> AcknowledgeOut:
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        raise ValueError("Policy not found")
    if policy.status != PolicyStatusEnum.active:
        raise ValueError("Only Active policies can be acknowledged")

    existing = db.query(PolicyAcknowledgement).filter(
        PolicyAcknowledgement.policy_id   == policy_id,
        PolicyAcknowledgement.employee_id == employee_id,
    ).first()

    if existing:
        return AcknowledgeOut(
            policy_id=existing.policy_id,
            employee_id=existing.employee_id,
            acked_at=existing.acked_at,
        )

    try:
        ack = PolicyAcknowledgement(policy_id=policy_id, employee_id=employee_id)
        db.add(ack)
        db.commit()
        db.refresh(ack)
        return AcknowledgeOut(
            policy_id=ack.policy_id,
            employee_id=ack.employee_id,
            acked_at=ack.acked_at,
        )
    except IntegrityError:
        db.rollback()
        existing = db.query(PolicyAcknowledgement).filter(
            PolicyAcknowledgement.policy_id   == policy_id,
            PolicyAcknowledgement.employee_id == employee_id,
        ).first()
        return AcknowledgeOut(
            policy_id=existing.policy_id,
            employee_id=existing.employee_id,
            acked_at=existing.acked_at,
        )


def get_employee_acks(db: Session, employee_id: int) -> List[int]:
    rows = db.query(PolicyAcknowledgement.policy_id).filter(
        PolicyAcknowledgement.employee_id == employee_id
    ).all()
    return [r[0] for r in rows]


# ═══════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════

def get_policy_stats(db: Session) -> PolicyStats:
    policies = (
        db.query(Policy)
        .filter(Policy.is_deleted == False)
        .all()
    )

    active = [p for p in policies if p.status == PolicyStatusEnum.active]
    rates  = []
    for p in active:
        tr = _total_recipients(db, p.audience)
        ac = _ack_count(db, p.id)
        if tr > 0:
            rates.append(ac / tr * 100)

    avg_rate = round(sum(rates) / len(rates), 1) if rates else 0.0
    pending  = len([p for p in policies if p.status == PolicyStatusEnum.review])

    return PolicyStats(
        total            = len(policies),
        active           = len([p for p in policies if p.status == PolicyStatusEnum.active]),
        draft            = len([p for p in policies if p.status == PolicyStatusEnum.draft]),
        review           = len([p for p in policies if p.status == PolicyStatusEnum.review]),
        archived         = len([p for p in policies if p.status == PolicyStatusEnum.archived]),
        mandatory        = len([p for p in policies if p.mandatory]),
        avg_ack_rate     = avg_rate,
        pending_approval = pending,
    )