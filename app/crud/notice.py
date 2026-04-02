"""
app/crud/notice.py

CRUD + business logic for the Notice Board module.

Key design decisions
════════════════════

1.  Audience scoping
    ─────────────────
    audience_type = "all"         → all active, non-deleted employees
    audience_type = "departments" → employees whose dept is in notice_audience_depts
    audience_type = "roles"       → employees whose role.name is in audience_roles (CSV)
    audience_type = "selective"   → employees whose id is in extra_data["employee_ids"]

2.  total_recipients
    ─────────────────
    Computed live from the employees table each call.
    Respects employment_status = "active" and is_deleted = False.

3.  ack_count
    ──────────
    COUNT(*) from notice_acknowledgements for this notice_id.

4.  Employee notice list
    ─────────────────────
    get_my_notices() — audience-scoped, active, non-expired notices
    annotated with acknowledged=True/False for the requesting employee.
    Pinned notices always first; then by created_at desc.

5.  Department audience update
    ───────────────────────────
    When updating audience, old NoticeAudienceDept rows are deleted
    and new ones are inserted atomically within the same transaction.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, or_, select, cast, Text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.notice import (
    Notice, NoticeAudienceDept, NoticeAcknowledgement,
    NoticeAudienceTypeEnum, NoticePriorityEnum,
)
from app.schemas.notice import (
    NoticeCreate, NoticeUpdate,
    NoticeListItem, NoticeOut,
    NoticeStats, AcknowledgeOut,
    EmployeeNoticeItem,
)
from app.core.email_sender import send_email
 

# ═══════════════════════════════════════════════════════════════════
# EMAIL HELPERS
# ═══════════════════════════════════════════════════════════════════

def _get_notice_recipients(db: Session, notice: Notice) -> List[tuple]:
    """
    Returns list of (employee_id, email) tuples for this notice's audience.
    Respects employment_status = 'active' and is_deleted = False.
    Returns empty list if email_sender is not available.
    """
    try:
        from app.models.employee import Employee
        from app.models.department import Department
        from app.models.role import Role

        base_query = db.query(Employee.id, Employee.email).filter(
            Employee.is_deleted == False,
            Employee.employment_status == "active",
            Employee.email != None,  # Only consider employees with email
        )

        if notice.audience_type == NoticeAudienceTypeEnum.all:
            return base_query.all()

        if notice.audience_type == NoticeAudienceTypeEnum.departments:
            dept_ids = [nd.department_id for nd in notice.audience_departments]
            if not dept_ids:
                return []
            return base_query.filter(Employee.department_id.in_(dept_ids)).all()

        if notice.audience_type == NoticeAudienceTypeEnum.roles:
            roles_csv = notice.audience_roles or ""
            role_names = [r.strip() for r in roles_csv.split(",") if r.strip()]
            if not role_names:
                return []
            return (
                base_query.join(Role, Employee.role_id == Role.id)
                .filter(Role.name.in_(role_names))
                .all()
            )

        if notice.audience_type == NoticeAudienceTypeEnum.selective:
            emp_ids = (notice.extra_data or {}).get("employee_ids", [])
            if not emp_ids:
                return []
            return base_query.filter(Employee.id.in_(emp_ids)).all()

        return []
    except Exception as e:
        print(f"Error getting notice recipients: {e}")
        return []


def _send_notice_emails(db: Session, notice: Notice):
    """
    Send email notifications for a notice to all eligible recipients.
    Silently fails if email is not configured.
    """
    if not notice.send_email:
        return

    recipients = _get_notice_recipients(db, notice)
    if not recipients:
        return

    # Format email subject and body
    subject = f"Notice: {notice.title} [{notice.priority.value}]"
    
    body = f"""Dear Employee,

We have a new notice for you:

Title: {notice.title}
Category: {notice.category.value}
Priority: {notice.priority.value}

Content:
{notice.content}

"""
    
    if notice.expires_at:
        body += f"Expires At: {notice.expires_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

    body += """
---
Please log in to your portal to acknowledge this notice.

Best regards,
HR Management System
"""

    # Send email to each recipient
    for emp_id, email in recipients:
        if email:
            try:
                send_email(email, subject, body)
            except Exception as e:
                print(f"Error sending notice email to {email}: {e}")





# ═══════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════

def _ack_count(db: Session, notice_id: int) -> int:
    return db.query(func.count(NoticeAcknowledgement.id)).filter(
        NoticeAcknowledgement.notice_id == notice_id
    ).scalar() or 0


def _total_recipients(db: Session, notice: Notice) -> int:
    """Count how many eligible employees this notice targets."""
    try:
        from app.models.employee import Employee
        from app.models.department import Department
        from app.models.role import Role

        base = db.query(func.count(Employee.id)).filter(
            Employee.is_deleted == False,
            Employee.employment_status == "active",
        )

        if notice.audience_type == NoticeAudienceTypeEnum.all:
            return base.scalar() or 0

        if notice.audience_type == NoticeAudienceTypeEnum.departments:
            dept_ids = [nd.department_id for nd in notice.audience_departments]
            if not dept_ids:
                return 0
            return (
                base.filter(Employee.department_id.in_(dept_ids))
                .scalar() or 0
            )

        if notice.audience_type == NoticeAudienceTypeEnum.roles:
            roles_csv = notice.audience_roles or ""
            role_names = [r.strip() for r in roles_csv.split(",") if r.strip()]
            if not role_names:
                return 0
            return (
                base.join(Role, Employee.role_id == Role.id)
                .filter(Role.name.in_(role_names))
                .scalar() or 0
            )

        if notice.audience_type == NoticeAudienceTypeEnum.selective:
            emp_ids = (notice.extra_data or {}).get("employee_ids", [])
            if not emp_ids:
                return 0
            return (
                base.filter(Employee.id.in_(emp_ids))
                .scalar() or 0
            )

        return 0
    except Exception:
        return 0


def _author_name(notice: Notice) -> Optional[str]:
    if notice.author:
        return f"{notice.author.f_name} {notice.author.l_name}".strip()
    return None


def _dept_info(notice: Notice):
    dept_ids   = [nd.department_id for nd in notice.audience_departments]
    dept_names = []
    for nd in notice.audience_departments:
        if nd.department:
            dept_names.append(nd.department.department)
    return dept_ids, dept_names


def _roles_list(notice: Notice) -> List[str]:
    if not notice.audience_roles:
        return []
    return [r.strip() for r in notice.audience_roles.split(",") if r.strip()]


def _emp_ids_list(notice: Notice) -> List[int]:
    return (notice.extra_data or {}).get("employee_ids", [])


def _to_list_item(db: Session, notice: Notice) -> NoticeListItem:
    dept_ids, dept_names = _dept_info(notice)
    return NoticeListItem(
        id               = notice.id,
        title            = notice.title,
        category         = notice.category.value,
        priority         = notice.priority.value,
        audience_type    = notice.audience_type.value,
        pinned           = notice.pinned,
        is_active        = notice.is_active,
        expires_at       = notice.expires_at,
        created_by       = notice.created_by,
        created_by_name  = _author_name(notice),
        created_at       = notice.created_at,
        updated_at       = notice.updated_at,
        ack_count        = _ack_count(db, notice.id),
        total_recipients = _total_recipients(db, notice),
        department_ids   = dept_ids,
        department_names = dept_names,
        audience_roles   = _roles_list(notice),
        employee_ids     = _emp_ids_list(notice),
    )


def _to_out(db: Session, notice: Notice) -> NoticeOut:
    dept_ids, dept_names = _dept_info(notice)
    return NoticeOut(
        id               = notice.id,
        title            = notice.title,
        content          = notice.content,
        category         = notice.category.value,
        priority         = notice.priority.value,
        audience_type    = notice.audience_type.value,
        pinned           = notice.pinned,
        is_active        = notice.is_active,
        expires_at       = notice.expires_at,
        created_by       = notice.created_by,
        created_by_name  = _author_name(notice),
        created_at       = notice.created_at,
        updated_at       = notice.updated_at,
        ack_count        = _ack_count(db, notice.id),
        total_recipients = _total_recipients(db, notice),
        extra_data       = notice.extra_data,
        department_ids   = dept_ids,
        department_names = dept_names,
        audience_roles   = _roles_list(notice),
        employee_ids     = _emp_ids_list(notice),
    )


def _base_query(db: Session):
    return (
        db.query(Notice)
        .options(
            joinedload(Notice.author),
            joinedload(Notice.audience_departments).joinedload(NoticeAudienceDept.department),
        )
        .filter(Notice.is_deleted == False)
    )


def _sync_dept_audience(db: Session, notice: Notice, dept_ids: List[int]):
    """Replace existing department audience rows with new ones."""
    db.query(NoticeAudienceDept).filter(
        NoticeAudienceDept.notice_id == notice.id
    ).delete(synchronize_session=False)
    for dept_id in dept_ids:
        db.add(NoticeAudienceDept(notice_id=notice.id, department_id=dept_id))


# ═══════════════════════════════════════════════════════════════════
# CREATE
# ═══════════════════════════════════════════════════════════════════

def create_notice(db: Session, data: NoticeCreate, created_by: int) -> NoticeOut:
    # Build extra_data
    extra = dict(data.extra_data or {})
    if data.audience_type == NoticeAudienceTypeEnum.selective and data.employee_ids:
        extra["employee_ids"] = data.employee_ids

    # Build roles CSV
    roles_csv = ",".join(data.audience_roles) if data.audience_roles else None

    notice = Notice(
        title         = data.title.strip(),
        content       = data.content.strip(),
        category      = data.category,
        priority      = data.priority,
        audience_type = data.audience_type,
        audience_roles = roles_csv,
        pinned        = data.pinned,
        is_active     = data.is_active,
        send_email    = data.send_email,
        expires_at    = data.expires_at,
        created_by    = created_by,
        extra_data    = extra or None,
    )
    db.add(notice)
    db.flush()  # get notice.id

    # Department audience
    if data.audience_type == NoticeAudienceTypeEnum.departments and data.department_ids:
        for dept_id in data.department_ids:
            db.add(NoticeAudienceDept(notice_id=notice.id, department_id=dept_id))

    db.commit()
    db.refresh(notice)
    
    # Send emails if requested
    _send_notice_emails(db, notice)
    
    return _to_out(db, notice)


# ═══════════════════════════════════════════════════════════════════
# READ
# ═══════════════════════════════════════════════════════════════════

def get_notice_by_id_raw(db: Session, notice_id: int) -> Optional[Notice]:
    return (
        _base_query(db)
        .filter(Notice.id == notice_id)
        .first()
    )


def get_notice_detail(db: Session, notice_id: int) -> Optional[NoticeOut]:
    notice = get_notice_by_id_raw(db, notice_id)
    if not notice:
        return None
    return _to_out(db, notice)


def list_notices(
    db: Session,
    # Admin sees all; employee sees only scoped active notices
    is_admin: bool = True,
    # Employee context (for scoping)
    employee_dept_id:   Optional[int] = None,
    employee_role_name: Optional[str] = None,
    employee_id:        Optional[int] = None,
    # Filters
    category:    Optional[str]  = None,
    priority:    Optional[str]  = None,
    audience_type: Optional[str] = None,
    is_active:   Optional[bool] = None,
    search:      Optional[str]  = None,
    skip: int = 0,
    limit: int = 100,
) -> List[NoticeListItem]:
    q = _base_query(db)

    if not is_admin:
        # Employees see only active, non-expired notices
        now = datetime.utcnow()
        q = q.filter(
            Notice.is_active == True,
            or_(Notice.expires_at == None, Notice.expires_at > now),
        )
        # Audience scoping
        conditions = [Notice.audience_type == NoticeAudienceTypeEnum.all]
        if employee_dept_id:
            # Notice has this dept in its audience_departments
            dept_subq = (
                select(NoticeAudienceDept.notice_id)
                .where(NoticeAudienceDept.department_id == employee_dept_id)
            )
            conditions.append(
                (Notice.audience_type == NoticeAudienceTypeEnum.departments) &
                Notice.id.in_(dept_subq)
            )
        if employee_role_name:
            conditions.append(
                (Notice.audience_type == NoticeAudienceTypeEnum.roles) &
                Notice.audience_roles.ilike(f"%{employee_role_name}%")
            )
        if employee_id:
            # Selective: employee id must appear in extra_data.employee_ids
            # We do a JSON contains check (PostgreSQL specific)
            # Fallback: cast to text and ilike
            conditions.append(
                (Notice.audience_type == NoticeAudienceTypeEnum.selective) &
                cast(Notice.extra_data, Text).ilike(f"%{employee_id}%")
            )
        q = q.filter(or_(*conditions))
    else:
        if is_active is not None:
            q = q.filter(Notice.is_active == is_active)

    if category:
        q = q.filter(Notice.category == category)
    if priority:
        q = q.filter(Notice.priority == priority)
    if audience_type and is_admin:
        q = q.filter(Notice.audience_type == audience_type)
    if search:
        term = f"%{search.lower()}%"
        q = q.filter(
            Notice.title.ilike(term) | Notice.content.ilike(term)
        )

    q = q.order_by(Notice.pinned.desc(), Notice.created_at.desc())
    notices = q.offset(skip).limit(limit).all()
    return [_to_list_item(db, n) for n in notices]


# ═══════════════════════════════════════════════════════════════════
# EMPLOYEE-FACING LIST with ack status
# ═══════════════════════════════════════════════════════════════════

def get_my_notices(
    db: Session,
    employee_id:        int,
    employee_dept_id:   Optional[int] = None,
    employee_role_name: Optional[str] = None,
    category:  Optional[str]  = None,
    priority:  Optional[str]  = None,
    search:    Optional[str]  = None,
) -> List[EmployeeNoticeItem]:
    now = datetime.utcnow()
    q = (
        _base_query(db)
        .filter(
            Notice.is_active == True,
            or_(Notice.expires_at == None, Notice.expires_at > now),
        )
    )

    # Audience scoping
    conditions = [Notice.audience_type == NoticeAudienceTypeEnum.all]

    if employee_dept_id:
        dept_subq = (
            select(NoticeAudienceDept.notice_id)
            .where(NoticeAudienceDept.department_id == employee_dept_id)
        )
        conditions.append(
            (Notice.audience_type == NoticeAudienceTypeEnum.departments) &
            Notice.id.in_(dept_subq)
        )

    if employee_role_name:
        conditions.append(
            (Notice.audience_type == NoticeAudienceTypeEnum.roles) &
            Notice.audience_roles.ilike(f"%{employee_role_name}%")
        )

    conditions.append(
        (Notice.audience_type == NoticeAudienceTypeEnum.selective) &
        cast(Notice.extra_data, Text).ilike(f"%{employee_id}%")
    )

    q = q.filter(or_(*conditions))

    if category:
        q = q.filter(Notice.category == category)
    if priority:
        q = q.filter(Notice.priority == priority)
    if search:
        term = f"%{search.lower()}%"
        q = q.filter(Notice.title.ilike(term) | Notice.content.ilike(term))

    q = q.order_by(Notice.pinned.desc(), Notice.created_at.desc())
    notices = q.all()

    # Batch-load acks for this employee
    notice_ids = [n.id for n in notices]
    acks = {}
    if notice_ids:
        rows = (
            db.query(NoticeAcknowledgement)
            .filter(
                NoticeAcknowledgement.employee_id == employee_id,
                NoticeAcknowledgement.notice_id.in_(notice_ids),
            )
            .all()
        )
        acks = {r.notice_id: r.acked_at for r in rows}

    result = []
    for n in notices:
        result.append(EmployeeNoticeItem(
            id               = n.id,
            title            = n.title,
            content          = n.content,
            category         = n.category.value,
            priority         = n.priority.value,
            audience_type    = n.audience_type.value,
            pinned           = n.pinned,
            expires_at       = n.expires_at,
            created_by_name  = _author_name(n),
            created_at       = n.created_at,
            updated_at       = n.updated_at,
            ack_count        = _ack_count(db, n.id),
            total_recipients = _total_recipients(db, n),
            acknowledged     = n.id in acks,
            acked_at         = acks.get(n.id),
        ))
    return result


# ═══════════════════════════════════════════════════════════════════
# UPDATE
# ═══════════════════════════════════════════════════════════════════

def update_notice(db: Session, notice_id: int, data: NoticeUpdate) -> Optional[NoticeOut]:
    notice = get_notice_by_id_raw(db, notice_id)
    if not notice:
        return None

    update_data = data.model_dump(exclude_unset=True)

    # Handle audience-specific fields separately
    dept_ids   = update_data.pop("department_ids", None)
    role_names = update_data.pop("audience_roles", None)
    emp_ids    = update_data.pop("employee_ids", None)

    # Check if send_email is being set to True (for sending emails on update)
    send_email_now = update_data.get("send_email", False) and not notice.send_email

    for field, value in update_data.items():
        if field != "extra_data":
            setattr(notice, field, value)

    # Update roles CSV
    if role_names is not None:
        notice.audience_roles = ",".join(role_names) if role_names else None

    # Update extra_data for selective audience
    if emp_ids is not None:
        extra = dict(notice.extra_data or {})
        extra["employee_ids"] = emp_ids
        notice.extra_data = extra
    elif "extra_data" in update_data:
        notice.extra_data = update_data["extra_data"]

    # Sync department audience
    if dept_ids is not None:
        _sync_dept_audience(db, notice, dept_ids)

    notice.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(notice)
    
    # Send emails if send_email was just enabled
    if send_email_now:
        _send_notice_emails(db, notice)
    
    return _to_out(db, notice)


# ═══════════════════════════════════════════════════════════════════
# PIN TOGGLE
# ═══════════════════════════════════════════════════════════════════

def toggle_pin(db: Session, notice_id: int) -> Optional[NoticeOut]:
    notice = get_notice_by_id_raw(db, notice_id)
    if not notice:
        return None
    notice.pinned     = not notice.pinned
    notice.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(notice)
    return _to_out(db, notice)


# ═══════════════════════════════════════════════════════════════════
# TOGGLE ACTIVE
# ═══════════════════════════════════════════════════════════════════

def toggle_active(db: Session, notice_id: int) -> Optional[NoticeOut]:
    notice = get_notice_by_id_raw(db, notice_id)
    if not notice:
        return None
    notice.is_active  = not notice.is_active
    notice.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(notice)
    return _to_out(db, notice)


# ═══════════════════════════════════════════════════════════════════
# DELETE (soft)
# ═══════════════════════════════════════════════════════════════════

def delete_notice(db: Session, notice_id: int) -> bool:
    notice = get_notice_by_id_raw(db, notice_id)
    if not notice:
        return False
    notice.is_deleted = True
    notice.updated_at = datetime.utcnow()
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════
# ACKNOWLEDGE
# ═══════════════════════════════════════════════════════════════════

def acknowledge_notice(
    db: Session,
    notice_id: int,
    employee_id: int,
) -> AcknowledgeOut:
    notice = get_notice_by_id_raw(db, notice_id)
    if not notice:
        raise ValueError("Notice not found")
    if not notice.is_active or notice.is_deleted:
        raise ValueError("This notice is no longer active")

    existing = db.query(NoticeAcknowledgement).filter(
        NoticeAcknowledgement.notice_id   == notice_id,
        NoticeAcknowledgement.employee_id == employee_id,
    ).first()

    if existing:
        return AcknowledgeOut(
            notice_id=existing.notice_id,
            employee_id=existing.employee_id,
            acked_at=existing.acked_at,
        )

    try:
        ack = NoticeAcknowledgement(notice_id=notice_id, employee_id=employee_id)
        db.add(ack)
        db.commit()
        db.refresh(ack)
        return AcknowledgeOut(
            notice_id=ack.notice_id,
            employee_id=ack.employee_id,
            acked_at=ack.acked_at,
        )
    except IntegrityError:
        db.rollback()
        existing = db.query(NoticeAcknowledgement).filter(
            NoticeAcknowledgement.notice_id   == notice_id,
            NoticeAcknowledgement.employee_id == employee_id,
        ).first()
        return AcknowledgeOut(
            notice_id=existing.notice_id,
            employee_id=existing.employee_id,
            acked_at=existing.acked_at,
        )


def get_employee_acked_notice_ids(db: Session, employee_id: int) -> List[int]:
    rows = db.query(NoticeAcknowledgement.notice_id).filter(
        NoticeAcknowledgement.employee_id == employee_id
    ).all()
    return [r[0] for r in rows]


# ═══════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════

def get_notice_stats(db: Session) -> NoticeStats:
    notices = (
        db.query(Notice)
        .options(joinedload(Notice.audience_departments))
        .filter(Notice.is_deleted == False)
        .all()
    )

    active  = [n for n in notices if n.is_active]
    pinned  = [n for n in notices if n.pinned]
    urgent  = [n for n in notices if n.priority == NoticePriorityEnum.urgent]

    rates = []
    for n in active:
        tr = _total_recipients(db, n)
        ac = _ack_count(db, n.id)
        if tr > 0:
            rates.append(ac / tr * 100)

    return NoticeStats(
        total        = len(notices),
        active       = len(active),
        pinned       = len(pinned),
        urgent       = len(urgent),
        avg_ack_rate = round(sum(rates) / len(rates), 1) if rates else 0.0,
    )