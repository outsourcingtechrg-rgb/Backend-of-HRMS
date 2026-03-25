"""
attendance.py  –  CRUD + processing logic

═══════════════════════════════════════════════════════════════════
CRITICAL: ID mapping
═══════════════════════════════════════════════════════════════════

  Attendance.employee_id   ← ZKT MACHINE ID  =  Employee.employee_id
                             NOT Employee.id (the DB primary key)

  /me endpoints receive Employee.id (from JWT).
  They call _resolve_machine_id() which converts to Employee.employee_id
  before touching the Attendance table.

  Admin endpoints work directly with machine IDs but always filter
  results through _known_machine_ids() so only current system
  employees appear — ex-employees / test entries in ZKT are excluded.

═══════════════════════════════════════════════════════════════════
Enriched admin records
═══════════════════════════════════════════════════════════════════
  get_admin_records()  →  List[dict]
    Each dict = logical AttendanceRecord + employee metadata:
      employee_name, f_name, l_name, designation,
      department_id, department_name, employment_status, image

  get_admin_summary()  →  dict
    Aggregated counts for the whole org (or one employee).

═══════════════════════════════════════════════════════════════════
Status rules
═══════════════════════════════════════════════════════════════════
  Absent  : no IN punch
  Late    : IN > shift.shift_late_on           (explicit config)
            IN > shift.shift_start + 15 min    (grace fallback)
            IN > 09:15                          (no shift)
  Early   : out_time present AND worked < shift.total_hours
  Present : on time, full hours
"""

from sqlalchemy.orm import Session
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Set, Dict
from calendar import monthrange

from app.models.attendance import Attendance
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate


# ═══════════════════════════════════════════════════════════════════
# EMPLOYEE RESOLUTION
# ═══════════════════════════════════════════════════════════════════

def _known_machine_ids(db: Session) -> Set[int]:
    """
    Set of Employee.employee_id values for non-deleted employees
    that actually have a machine ID enrolled in ZKT.
    Used everywhere to exclude ghost/test entries.
    """
    try:
        from app.models.employee import Employee
        rows = (
            db.query(Employee.employee_id)
            .filter(
                Employee.employee_id.isnot(None),
                Employee.is_deleted == False,
            )
            .all()
        )
        return {r[0] for r in rows}
    except Exception:
        return set()


def _resolve_machine_id(db: Session, employee_id: int) -> Optional[int]:
    """
    Convert whatever the caller passes (Employee.id or Employee.employee_id)
    to the ZKT machine ID (Employee.employee_id).

    Priority:
      1. Find by Employee.id  →  return its employee_id (machine ID)
      2. Find by Employee.employee_id directly  →  return as-is
      3. Not found  →  return None
    """
    try:
        from app.models.employee import Employee

        # Try DB primary key first (JWT sends Employee.id)
        emp = db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.is_deleted == False,
        ).first()
        if emp is not None:
            return emp.employee_id  # may be None if not enrolled in ZKT

        # Try as machine ID directly (admin endpoints, ZKT sync)
        emp = db.query(Employee).filter(
            Employee.employee_id == employee_id,
            Employee.is_deleted == False,
        ).first()
        if emp is not None:
            return emp.employee_id

        return None
    except Exception:
        return None


def _get_shift_for_machine_id(db: Session, machine_id: int):
    """Load Shift ORM for the employee with this ZKT machine ID."""
    try:
        from app.models.employee import Employee
        emp = db.query(Employee).filter(
            Employee.employee_id == machine_id,
            Employee.is_deleted == False,
        ).first()
        return emp.shift if emp else None
    except Exception:
        return None


def _load_employee_map(db: Session) -> Dict[int, dict]:
    """
    Build machine_id → employee metadata dict for all non-deleted
    employees that have a machine ID.

    Shape:
        { machine_id: {
            "db_id":             int,
            "f_name":            str,
            "l_name":            str,
            "full_name":         str,
            "designation":       str | None,
            "department_id":     int | None,
            "department_name":   str | None,
            "employment_status": str,
            "image":             str | None,
        }}
    """
    try:
        from app.models.employee import Employee
        from app.models.department import Department

        rows = (
            db.query(Employee, Department.department)
            .outerjoin(Department, Employee.department_id == Department.id)
            .filter(
                Employee.employee_id.isnot(None),
                Employee.is_deleted == False,
            )
            .all()
        )

        result = {}
        for emp, dept_name in rows:
            result[emp.employee_id] = {
                "db_id":             emp.id,
                "f_name":            emp.f_name,
                "l_name":            emp.l_name,
                "full_name":         f"{emp.f_name} {emp.l_name}".strip(),
                "designation":       emp.designation,
                "department_id":     emp.department_id,
                "department_name":   dept_name,
                "employment_status": emp.employment_status.value
                                     if hasattr(emp.employment_status, "value")
                                     else str(emp.employment_status),
                "image":             emp.image,
            }
        return result
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════════
# BASIC CRUD  (raw punch rows — unchanged semantics)
# ═══════════════════════════════════════════════════════════════════

def create_attendance(db: Session, data: AttendanceCreate) -> Attendance:
    obj = Attendance(**data.dict(), synced_at=datetime.utcnow())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def bulk_create_attendance(db: Session, records: List[AttendanceCreate]) -> List[Attendance]:
    now  = datetime.utcnow()
    objs = [Attendance(**r.dict(), synced_at=now) for r in records]
    db.add_all(objs)
    db.commit()
    for o in objs:
        db.refresh(o)
    return objs


def get_attendance_by_id(db: Session, attendance_id: int) -> Optional[Attendance]:
    return db.query(Attendance).filter(Attendance.id == attendance_id).first()


def update_attendance(db: Session, attendance_id: int, data: AttendanceUpdate) -> Optional[Attendance]:
    obj = get_attendance_by_id(db, attendance_id)
    if not obj:
        return None
    for key, value in data.dict(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_attendance(db: Session, attendance_id: int) -> bool:
    obj = get_attendance_by_id(db, attendance_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


def get_attendances(
    db: Session,
    employee_id: Optional[int] = None,
    attendance_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Attendance]:
    """
    Raw punch rows.  Always filtered to known employees.
    employee_id is treated as machine ID when provided.
    """
    q = db.query(Attendance)

    if employee_id is not None:
        q = q.filter(Attendance.employee_id == employee_id)
    else:
        known = _known_machine_ids(db)
        if known:
            q = q.filter(Attendance.employee_id.in_(known))
        else:
            # No known employees → return nothing rather than all raw ZKT data
            return []

    if attendance_date:
        q = q.filter(Attendance.attendance_date == attendance_date)

    return q.order_by(Attendance.attendance_date.desc()).offset(skip).limit(limit).all()


def get_attendance_by_employee_and_date(
    db: Session, employee_id: int, attendance_date: date
) -> List[Attendance]:
    return (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee_id,
            Attendance.attendance_date == attendance_date,
        )
        .all()
    )


def get_last_synced_time(db: Session) -> Optional[datetime]:
    rec = (
        db.query(Attendance)
        .filter(Attendance.synced_at.isnot(None))
        .order_by(Attendance.synced_at.desc())
        .first()
    )
    return rec.synced_at if rec else None


# ═══════════════════════════════════════════════════════════════════
# PROCESSING HELPERS
# ═══════════════════════════════════════════════════════════════════

def _to_mins(t: Optional[time]) -> Optional[int]:
    return (t.hour * 60 + t.minute) if t else None


def _is_overnight(shift) -> bool:
    if shift is None:
        return False
    s = _to_mins(shift.shift_start_timing)
    e = _to_mins(shift.shift_end_timing)
    return s is not None and e is not None and e < s


def _late_threshold(shift) -> time:
    if shift and shift.shift_late_on:
        return shift.shift_late_on
    if shift and shift.shift_start_timing:
        grace = _to_mins(shift.shift_start_timing) + 15
        return time(grace // 60 % 24, grace % 60)
    return time(9, 15)


def _time_to_seconds(value: Optional[time]) -> Optional[int]:
    if value is None:
        return None
    return value.hour * 3600 + value.minute * 60 + value.second


def _is_early_by_hours(shift, hours: Optional[float]) -> bool:
    if shift is None or hours is None:
        return False
    required = _time_to_seconds(shift.total_hours)
    if required is None:
        return False
    return int(hours * 3600) < required


def _logical_record_date(punch: Attendance, shift) -> date:
    """
    For overnight shifts: punches after midnight that fall within the
    shift's end + 5 h window belong to the previous calendar day.
    """
    if not shift or not _is_overnight(shift):
        return punch.attendance_date

    end_mins    = _to_mins(shift.shift_end_timing)
    cutoff_mins = (end_mins + 300) % (24 * 60)
    punch_mins  = _to_mins(punch.attendance_time)

    if punch_mins is not None and punch_mins <= cutoff_mins:
        return punch.attendance_date - timedelta(days=1)

    return punch.attendance_date


# ═══════════════════════════════════════════════════════════════════
# CORE: raw punches → logical AttendanceRecord dicts
# ═══════════════════════════════════════════════════════════════════

def _build_records(punches: List[Attendance], shift=None) -> List[dict]:
    """
    Convert raw ZKT punch rows into logical attendance records.
    Each record is dated on the IN-punch date.
    """
    if not punches:
        return []

    overnight   = _is_overnight(shift)
    threshold   = _late_threshold(shift)
    max_gap_sec = (16 if overnight else 14) * 3600

    # Group by logical work date
    buckets: Dict[date, List[Attendance]] = {}
    for punch in punches:
        d = _logical_record_date(punch, shift)
        buckets.setdefault(d, []).append(punch)

    result: List[dict] = []
    dt_key = lambda p: datetime.combine(p.attendance_date, p.attendance_time)

    for record_date, bucket in buckets.items():
        ordered = sorted(bucket, key=dt_key)
        ins  = [p for p in ordered if p.punch is False]
        outs = [p for p in ordered if p.punch is True]

        inp  = ins[0] if ins else None
        outp = None

        if inp is not None:
            in_dt = datetime.combine(inp.attendance_date, inp.attendance_time)
            valid = [
                c for c in outs
                if 0 < (datetime.combine(c.attendance_date, c.attendance_time) - in_dt).total_seconds() <= max_gap_sec
            ]
            outp = valid[-1] if valid else None
        elif outs:
            outp = outs[-1]

        anchor   = inp or outp
        in_time  = inp.attendance_time  if inp  else None
        out_time = outp.attendance_time if outp else None
        in_date  = inp.attendance_date  if inp  else None
        out_date = outp.attendance_date if outp else None

        hours: Optional[float] = None
        if in_time and out_time and in_date and out_date:
            dt_in  = datetime.combine(in_date,  in_time)
            dt_out = datetime.combine(out_date, out_time)
            secs   = (dt_out - dt_in).total_seconds()
            if secs > 0:
                hours = round(secs / 3600, 2)

        if inp is None:
            status = "Absent"
        else:
            in_dt        = datetime.combine(inp.attendance_date, inp.attendance_time)
            threshold_dt = datetime.combine(record_date, threshold)
            if outp is not None and _is_early_by_hours(shift, hours):
                status = "Early"
            elif in_dt > threshold_dt:
                status = "Late"
            else:
                status = "Present"

        result.append({
            "id":              anchor.id,
            "employee_id":     anchor.employee_id,  # machine ID
            "date":            str(record_date),
            "status":          status,
            "in_time":         in_time.strftime("%H:%M")  if in_time  else None,
            "out_time":        out_time.strftime("%H:%M") if out_time else None,
            "hours":           hours,
            "note":            None,
            "attendance_mode": getattr(anchor, "attendance_mode", None),
        })

    return sorted(result, key=lambda x: x["date"], reverse=True)


# ═══════════════════════════════════════════════════════════════════
# USER /me ENDPOINTS
# employee_id = Employee.id (DB PK from JWT)
# ═══════════════════════════════════════════════════════════════════

def get_my_attendance(
    db: Session,
    employee_id: int,
    month: Optional[str] = None,
) -> List[dict]:
    """
    Logical attendance records for the requesting employee.
    employee_id = Employee.id (from JWT).
    Returns [] if employee has no ZKT enrollment.
    """
    machine_id = _resolve_machine_id(db, employee_id)
    if machine_id is None:
        return []

    shift     = _get_shift_for_machine_id(db, machine_id)
    overnight = _is_overnight(shift)

    q = db.query(Attendance).filter(Attendance.employee_id == machine_id)

    if month:
        year, mon  = map(int, month.split("-"))
        last_day   = monthrange(year, mon)[1]
        start_date = date(year, mon, 1)
        end_date   = date(year, mon, last_day)
        if overnight:
            start_date -= timedelta(days=1)
            end_date   += timedelta(days=1)
        q = q.filter(Attendance.attendance_date.between(start_date, end_date))

    raw     = q.all()
    records = _build_records(raw, shift=shift)

    if month:
        year, mon = map(int, month.split("-"))
        prefix    = f"{year}-{mon:02d}"
        records   = [r for r in records if r["date"].startswith(prefix)]

    return records


def get_today_attendance(
    db: Session,
    employee_id: int,
) -> Optional[dict]:
    """
    Today's logical record for the requesting employee.
    Returns None when outside shift window or not enrolled.
    employee_id = Employee.id (from JWT).
    """
    machine_id = _resolve_machine_id(db, employee_id)
    if machine_id is None:
        return None

    shift     = _get_shift_for_machine_id(db, machine_id)
    overnight = _is_overnight(shift)

    now       = datetime.now()
    today     = now.date()
    yesterday = today - timedelta(days=1)
    now_mins  = now.hour * 60 + now.minute

    if shift is None:
        raw   = db.query(Attendance).filter(
            Attendance.employee_id == machine_id,
            Attendance.attendance_date == today,
        ).all()
        built = _build_records(raw)
        return built[0] if built else None

    end_mins    = _to_mins(shift.shift_end_timing)
    start_mins  = _to_mins(shift.shift_start_timing)
    cutoff_mins = (end_mins + 300) % (24 * 60)

    if not overnight:
        if now_mins > cutoff_mins:
            return None
        raw   = db.query(Attendance).filter(
            Attendance.employee_id == machine_id,
            Attendance.attendance_date == today,
        ).all()
        built = _build_records(raw, shift=shift)
        return built[0] if built else None

    # Overnight: post-midnight or within cutoff
    if now_mins <= cutoff_mins:
        raw   = db.query(Attendance).filter(
            Attendance.employee_id == machine_id,
            Attendance.attendance_date.in_([yesterday, today]),
        ).all()
        built = _build_records(raw, shift=shift)
        return built[0] if built else None

    # Dead zone between cutoff and shift start
    if cutoff_mins < now_mins < start_mins:
        return None

    # Pre-midnight: shift has just started
    if now_mins >= start_mins:
        raw   = db.query(Attendance).filter(
            Attendance.employee_id == machine_id,
            Attendance.attendance_date == today,
        ).all()
        built = _build_records(raw, shift=shift)
        return built[0] if built else None

    return None


def get_attendance_summary(
    db: Session,
    employee_id: int,
    month: str,
) -> dict:
    """
    Monthly summary for one employee (Employee.id from JWT).
    """
    records    = get_my_attendance(db, employee_id, month=month)
    present    = sum(1 for r in records if r["status"] == "Present")
    late       = sum(1 for r in records if r["status"] == "Late")
    early      = sum(1 for r in records if r["status"] == "Early")
    absent     = sum(1 for r in records if r["status"] == "Absent")
    leave      = sum(1 for r in records if r["status"] == "Leave")
    total_days = len(records)
    rate       = round(((present + late + early) / total_days) * 100, 2) if total_days else 0.0

    return {
        "present":    present,
        "late":       late,
        "early":      early,
        "absent":     absent,
        "leave":      leave,
        "total_days": total_days,
        "rate":       rate,
    }


# ═══════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# Work across all system employees (filtered by _known_machine_ids).
# Records are enriched with employee name / dept / designation.
# ═══════════════════════════════════════════════════════════════════

def get_admin_records(
    db: Session,
    month: Optional[str] = None,
    employee_db_id: Optional[int] = None,
    department_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[dict]:
    """
    Return enriched logical attendance records for admin/HR views.

    Filters:
      month          — "YYYY-MM"  (recommended — large datasets otherwise)
      employee_db_id — Employee.id (DB PK) to scope to one employee
      department_id  — filter by department
      status_filter  — "Present" | "Late" | "Early" | "Absent" | "Leave"

    Returns dicts shaped as AttendanceRecord + employee metadata fields:
      employee_name, f_name, l_name, designation,
      department_id, department_name, employment_status, image

    Only employees that exist in the Employee table are included.
    ZKT ghost entries (machine IDs with no matching employee) are excluded.
    """
    # Build employee map (machine_id → metadata) — filters to known employees
    emp_map = _load_employee_map(db)

    if not emp_map:
        return []

    # Optional: scope to a single employee
    if employee_db_id is not None:
        machine_id = _resolve_machine_id(db, employee_db_id)
        if machine_id is None or machine_id not in emp_map:
            return []
        scope_ids = {machine_id}
    else:
        scope_ids = set(emp_map.keys())

    # Optional: scope to a department
    if department_id is not None:
        scope_ids = {
            mid for mid in scope_ids
            if emp_map[mid]["department_id"] == department_id
        }

    if not scope_ids:
        return []

    # Build date range
    start_date: Optional[date] = None
    end_date:   Optional[date] = None
    if month:
        year, mon  = map(int, month.split("-"))
        last_day   = monthrange(year, mon)[1]
        start_date = date(year, mon, 1)
        end_date   = date(year, mon, last_day)

    # Fetch raw punches for all scoped employees
    q = db.query(Attendance).filter(Attendance.employee_id.in_(scope_ids))
    if start_date and end_date:
        # Pad ±1 day to capture overnight shift boundary punches
        q = q.filter(
            Attendance.attendance_date.between(
                start_date - timedelta(days=1),
                end_date   + timedelta(days=1),
            )
        )

    all_punches = q.order_by(Attendance.attendance_date).all()

    # Group punches by machine_id
    by_emp: Dict[int, List[Attendance]] = {}
    for punch in all_punches:
        by_emp.setdefault(punch.employee_id, []).append(punch)

    # Process each employee's punches
    result: List[dict] = []
    for machine_id, punches in by_emp.items():
        meta  = emp_map.get(machine_id, {})
        shift = _get_shift_for_machine_id(db, machine_id)
        recs  = _build_records(punches, shift=shift)

        # Filter back to the requested month (IN-punch date)
        if month:
            year, mon = map(int, month.split("-"))
            prefix    = f"{year}-{mon:02d}"
            recs      = [r for r in recs if r["date"].startswith(prefix)]

        for rec in recs:
            # Apply status filter if requested
            if status_filter and rec["status"] != status_filter:
                continue

            result.append({
                **rec,
                # Employee metadata
                "employee_name":     meta.get("full_name", f"#{machine_id}"),
                "f_name":            meta.get("f_name"),
                "l_name":            meta.get("l_name"),
                "designation":       meta.get("designation"),
                "department_id":     meta.get("department_id"),
                "department_name":   meta.get("department_name"),
                "employment_status": meta.get("employment_status"),
                "image":             meta.get("image"),
                "employee_db_id":    meta.get("db_id"),
            })

    # Sort: most recent first, then by name
    result.sort(key=lambda x: (x["date"], x.get("employee_name", "")), reverse=True)

    # Paginate
    return result[skip : skip + limit]


def get_admin_summary(
    db: Session,
    month: str,
    department_id: Optional[int] = None,
) -> dict:
    """
    Organisation-wide (or department-wide) attendance summary for a month.

    Returns:
      {
        present, late, early, absent, leave,
        total_records, total_employees,
        rate,
        by_department: [{ department_id, department_name, present, total, rate }]
      }

    Only covers employees in the Employee table (not ghost ZKT entries).
    """
    records = get_admin_records(db, month=month, department_id=department_id, limit=10_000)

    present  = sum(1 for r in records if r["status"] == "Present")
    late     = sum(1 for r in records if r["status"] == "Late")
    early    = sum(1 for r in records if r["status"] == "Early")
    absent   = sum(1 for r in records if r["status"] == "Absent")
    leave    = sum(1 for r in records if r["status"] == "Leave")
    total    = len(records)
    rate     = round(((present + late + early) / total) * 100, 2) if total else 0.0

    # Per-department breakdown
    dept_map: Dict[Optional[int], dict] = {}
    for r in records:
        did   = r.get("department_id")
        dname = r.get("department_name") or "Unassigned"
        if did not in dept_map:
            dept_map[did] = {
                "department_id":   did,
                "department_name": dname,
                "present":         0,
                "total":           0,
            }
        dept_map[did]["total"] += 1
        if r["status"] in ("Present", "Late", "Early"):
            dept_map[did]["present"] += 1

    by_department = []
    for entry in dept_map.values():
        t = entry["total"]
        entry["rate"] = round((entry["present"] / t) * 100, 2) if t else 0.0
        by_department.append(entry)
    by_department.sort(key=lambda x: x.get("department_name") or "")

    return {
        "present":          present,
        "late":             late,
        "early":            early,
        "absent":           absent,
        "leave":            leave,
        "total_records":    total,
        "total_employees":  len({r["employee_id"] for r in records}),
        "rate":             rate,
        "by_department":    by_department,
    }