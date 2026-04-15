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
WHY ABSENTS WERE MISSING  (root-cause fix)
═══════════════════════════════════════════════════════════════════

  The ZKT machine only writes a row when someone punches in or out.
  A completely absent day produces ZERO rows in the attendance table.

  Old behaviour: _build_records() only iterated over days that had
  at least one punch, so absent days were invisible.

  Fix: _fill_absent_days() receives the set of "punched dates" and
  the full calendar range for the requested month. For every working
  day (Mon–Fri by default, or every day if the employee has no shift
  info) that has NO punch it synthesises a record:

      { "status": "Absent", "in_time": None, "out_time": None, "hours": None }

  Weekend handling:
    • If the employee's shift runs Mon–Fri we skip Sat/Sun.
    • If no shift info is available we mark ALL days Absent (safest).
    • Public holidays are NOT handled here (no holiday table yet).

═══════════════════════════════════════════════════════════════════
Status rules
═══════════════════════════════════════════════════════════════════
  Absent  : no punch row for that calendar day
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
    try:
        from app.models.employee import Employee

        emp = db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.is_deleted == False,
        ).first()
        if emp is not None:
            return emp.employee_id

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
                "employment_status": (
                    emp.employment_status.value
                    if hasattr(emp.employment_status, "value")
                    else str(emp.employment_status)
                ),
                "image":             emp.image,
            }
        return result
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════════
# BASIC CRUD  (raw punch rows)
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
    q = db.query(Attendance)

    if employee_id is not None:
        q = q.filter(Attendance.employee_id == employee_id)
    else:
        known = _known_machine_ids(db)
        if known:
            q = q.filter(Attendance.employee_id.in_(known))
        else:
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
    if not shift or not _is_overnight(shift):
        return punch.attendance_date

    end_mins    = _to_mins(shift.shift_end_timing)
    cutoff_mins = (end_mins + 300) % (24 * 60)
    punch_mins  = _to_mins(punch.attendance_time)

    if punch_mins is not None and punch_mins <= cutoff_mins:
        return punch.attendance_date - timedelta(days=1)

    return punch.attendance_date


def _is_working_day(d: date, shift) -> bool:
    """
    Return True if this calendar date is a working day.

    Rules (simple — no public-holiday table yet):
      • If the employee has shift info and shift_start is set, we trust
        that Mon–Fri are working days and Sat/Sun are not.
        (Most Pakistani / Gulf schedules are Mon–Fri or Sun–Thu; we
        default to Mon–Fri until a proper schedule model is added.)
      • If no shift info: mark every calendar day as a working day so we
        never silently drop absences.  HR can filter weekends on the
        frontend if needed.
    """
    if shift is None:
        # No shift → mark all days as potentially working
        return True

    # weekday(): 0=Mon … 6=Sun
    # Mon–Fri = 0–4  →  Sat(5) and Sun(6) are off by default
    return d.weekday() < 5


# ═══════════════════════════════════════════════════════════════════
# THE ABSENT-DAY SYNTHESISER  ← this is the key fix
# ═══════════════════════════════════════════════════════════════════

def _fill_absent_days(
    existing_records: List[dict],
    start_date: date,
    end_date: date,
    machine_id: int,
    shift,
) -> List[dict]:
    """
    For every working day in [start_date, end_date] that has NO
    matching record in existing_records, inject a synthetic Absent entry.

    This is what makes absent days visible.  Without this, only days
    with at least one ZKT punch ever appear in the output.

    Parameters
    ----------
    existing_records : records already built by _build_records()
    start_date       : first day of the requested range (already clamped to month)
    end_date         : last day of the requested range
    machine_id       : ZKT machine ID — used as employee_id in the synthetic record
    shift            : Shift ORM object or None — used to decide working days

    Returns
    -------
    Combined list (existing + absent synthetics), sorted newest-first.
    """
    today = datetime.utcnow().date()

    # Build a set of dates we already have records for
    existing_dates: Set[date] = set()
    for r in existing_records:
        try:
            existing_dates.add(date.fromisoformat(r["date"]))
        except (ValueError, TypeError):
            pass

    synthetic: List[dict] = []

    cur = start_date
    while cur <= end_date:
        # Don't synthesise absent for today or future dates —
        # the employee might still punch in.
        if cur >= today:
            cur += timedelta(days=1)
            continue

        if _is_working_day(cur, shift) and cur not in existing_dates:
            synthetic.append({
                "id":              None,   # no real DB row
                "employee_id":     machine_id,
                "date":            str(cur),
                "status":          "Absent",
                "in_time":         None,
                "out_time":        None,
                "hours":           None,
                "note":            None,
                "attendance_mode": None,
            })

        cur += timedelta(days=1)

    combined = existing_records + synthetic
    return sorted(combined, key=lambda x: x["date"], reverse=True)


# ═══════════════════════════════════════════════════════════════════
# CORE: raw punches → logical AttendanceRecord dicts
# ═══════════════════════════════════════════════════════════════════

def _build_records(punches: List[Attendance], shift=None) -> List[dict]:
    if not punches:
        return []

    from datetime import datetime, date

    overnight   = _is_overnight(shift)
    threshold   = _late_threshold(shift)
    max_gap_sec = (16 if overnight else 14) * 3600

    today = date.today()
    now   = datetime.now()

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

        # ---- OUT selection ----
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

        # ---- HOURS ----
        hours: Optional[float] = None
        if in_time and out_time and in_date and out_date:
            dt_in  = datetime.combine(in_date,  in_time)
            dt_out = datetime.combine(out_date, out_time)
            secs   = (dt_out - dt_in).total_seconds()
            if secs > 0:
                hours = round(secs / 3600, 2)

        # ===============================
        # ✅ TODAY LOGIC FIRST (IMPORTANT)
        # ===============================
        is_today_record = (
    record_date == today or
    (overnight and record_date == today - timedelta(days=1)))
        if is_today_record:
            if inp is None and outp is None:
                status = "Absent"

            elif inp is not None and outp is None:
                is_late = False

                if shift:
                    in_dt        = datetime.combine(inp.attendance_date, inp.attendance_time)
                    threshold_dt = datetime.combine(record_date, threshold)
                    is_late = in_dt > threshold_dt

                # still working?
                if shift:
                    shift_start = shift.shift_start_timing
                    shift_end   = shift.shift_end_timing

                    shift_start_dt = datetime.combine(record_date, shift_start)

                    if _is_overnight(shift):
                        shift_end_dt = datetime.combine(record_date + timedelta(days=1), shift_end)
                    else:
                        shift_end_dt = datetime.combine(record_date, shift_end)

                    if now < shift_end_dt:
                        status = "Present"
                    else:
                        status = "Late & Early" if is_late else "Early"
                else:
                    status = "Late & Early" if is_late else "Present"
                    
            elif inp is None and outp is not None:
                status = "Late"

            else:
                # both exist → calculate normally
                in_dt        = datetime.combine(inp.attendance_date, inp.attendance_time)
                threshold_dt = datetime.combine(record_date, threshold)

                is_late  = in_dt > threshold_dt
                is_early = _is_early_by_hours(shift, hours)

                if is_late and is_early:
                    status = "Late & Early"
                elif is_early:
                    status = "Early"
                elif is_late:
                    status = "Late"
                else:
                    status = "Present"

        # ===============================
        # ✅ PAST DAYS LOGIC
        # ===============================
        else:
            # both missing → Absent
            if inp is None and outp is None:
                status = "Absent"

            else:
                is_late  = False
                is_early = False

                # ---- LATE CHECK ----
                if inp is None:
                    # no IN → definitely late (came but no proper IN)
                    is_late = True
                else:
                    in_dt        = datetime.combine(inp.attendance_date, inp.attendance_time)
                    threshold_dt = datetime.combine(record_date, threshold)
                    is_late = in_dt > threshold_dt

                # ---- EARLY CHECK ----
                if outp is None:
                    # no OUT → definitely early (left without punching out)
                    is_early = True
                else:
                    is_early = _is_early_by_hours(shift, hours)

                # ---- FINAL STATUS ----
                if is_late and is_early:
                    status = "Late & Early"
                elif is_late:
                    status = "Late"
                elif is_early:
                    status = "Early"
                else:
                    status = "Present"
        result.append({
            "id":              anchor.id,
            "employee_id":     anchor.employee_id,
            "date":            str(record_date),
            "status":          status,
            "in_time":         in_time.strftime("%H:%M")  if in_time  else None,
            "out_time":        out_time.strftime("%H:%M") if out_time else None,
            "hours":           hours,
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

    Absent days are now included: every working day in the requested
    month that has no punch row is synthesised as an Absent record.
    """
    machine_id = _resolve_machine_id(db, employee_id)
    if machine_id is None:
        return []

    shift     = _get_shift_for_machine_id(db, machine_id)
    overnight = _is_overnight(shift)

    # Build the canonical date range for the requested month
    if month:
        year, mon  = map(int, month.split("-"))
        last_day   = monthrange(year, mon)[1]
        month_start = date(year, mon, 1)
        month_end   = date(year, mon, last_day)

        # Pad ±1 day for overnight shift boundary
        fetch_start = month_start - timedelta(days=1) if overnight else month_start
        fetch_end   = month_end   + timedelta(days=1) if overnight else month_end
    else:
        # No month filter — fetch all punches for the employee
        month_start = fetch_start = None
        month_end   = fetch_end   = None

    q = db.query(Attendance).filter(Attendance.employee_id == machine_id)

    if fetch_start and fetch_end:
        q = q.filter(Attendance.attendance_date.between(fetch_start, fetch_end))

    raw     = q.all()
    records = _build_records(raw, shift=shift)

    # Clamp back to the requested month (handles overnight boundary records)
    if month:
        prefix  = f"{year}-{mon:02d}"
        records = [r for r in records if r["date"].startswith(prefix)]

    # ── KEY FIX: inject Absent records for days with no punch ──
    if month and month_start and month_end:
        records = _fill_absent_days(
            existing_records=records,
            start_date=month_start,
            end_date=month_end,
            machine_id=machine_id,
            shift=shift,
        )

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

    if now_mins <= cutoff_mins:
        raw   = db.query(Attendance).filter(
            Attendance.employee_id == machine_id,
            Attendance.attendance_date.in_([yesterday, today]),
        ).all()
        built = _build_records(raw, shift=shift)
        return built[0] if built else None

    if cutoff_mins < now_mins < start_mins:
        return None

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
    Absent days are now counted correctly because get_my_attendance
    includes synthesised Absent records.
    """
    records    = get_my_attendance(db, employee_id, month=month)
    present    = sum(1 for r in records if r["status"] == "Present")
    late       = sum(1 for r in records if r["status"] in ("Late", "Late & Early"))
    early      = sum(1 for r in records if r["status"] in ("Early", "Late & Early"))
    absent     = sum(1 for r in records if r["status"] == "Absent")
    leave      = sum(1 for r in records if r["status"] == "Leave")
    total_days = len(records)
    attended   = sum(1 for r in records if r["status"] in ("Present", "Late", "Early", "Late & Early"))
    rate       = round((attended / total_days) * 100, 2) if total_days else 0.0

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
# Absent days are synthesised for each employee in scope.
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
    Enriched logical attendance records for admin/HR views.
    Now includes synthesised Absent rows for days with no punch.

    status_filter behaviour:
      "Late"  → includes both "Late" and "Late & Early"
      "Early" → includes both "Early" and "Late & Early"
      any other value → exact match only
    """
    emp_map = _load_employee_map(db)

    if not emp_map:
        return []

    if employee_db_id is not None:
        machine_id = _resolve_machine_id(db, employee_db_id)
        if machine_id is None or machine_id not in emp_map:
            return []
        scope_ids = {machine_id}
    else:
        scope_ids = set(emp_map.keys())

    if department_id is not None:
        scope_ids = {
            mid for mid in scope_ids
            if emp_map[mid]["department_id"] == department_id
        }

    if not scope_ids:
        return []

    # Determine canonical month range
    month_start: Optional[date] = None
    month_end:   Optional[date] = None
    if month:
        year, mon  = map(int, month.split("-"))
        last_day   = monthrange(year, mon)[1]
        month_start = date(year, mon, 1)
        month_end   = date(year, mon, last_day)

    # Fetch raw punches — pad ±1 day always (handles overnight across all shifts)
    q = db.query(Attendance).filter(Attendance.employee_id.in_(scope_ids))
    if month_start and month_end:
        q = q.filter(
            Attendance.attendance_date.between(
                month_start - timedelta(days=1),
                month_end   + timedelta(days=1),
            )
        )

    all_punches = q.order_by(Attendance.attendance_date).all()

    by_emp: Dict[int, List[Attendance]] = {}
    for punch in all_punches:
        by_emp.setdefault(punch.employee_id, []).append(punch)

    # Also ensure every scoped employee gets an entry even if they have
    # zero punches this month (they'll be all-Absent)
    for mid in scope_ids:
        by_emp.setdefault(mid, [])

    # Pre-compute which statuses pass the filter so we don't repeat
    # this logic inside the inner loop.
    def _status_passes(status: str) -> bool:
        if not status_filter:
            return True
        if status_filter in ("Late", "Early"):
            return status == status_filter or status == "Late & Early"
        return status == status_filter

    result: List[dict] = []

    for machine_id, punches in by_emp.items():
        meta  = emp_map.get(machine_id, {})
        shift = _get_shift_for_machine_id(db, machine_id)
        recs  = _build_records(punches, shift=shift)

        # Clamp to requested month
        if month and month_start and month_end:
            prefix = f"{year}-{mon:02d}"
            recs   = [r for r in recs if r["date"].startswith(prefix)]

        # ── KEY FIX: inject Absent records for this employee ──
        if month_start and month_end:
            recs = _fill_absent_days(
                existing_records=recs,
                start_date=month_start,
                end_date=month_end,
                machine_id=machine_id,
                shift=shift,
            )

        for rec in recs:
            if not _status_passes(rec["status"]):
                continue

            result.append({
                **rec,
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

    result.sort(key=lambda x: (x["date"], x.get("employee_name", "")), reverse=True)
    return result[skip : skip + limit]

def get_admin_summary(
    db: Session,
    month: str,
    department_id: Optional[int] = None,
) -> dict:
    """
    Organisation-wide (or department-wide) attendance summary.
    Absent counts are now correct because get_admin_records injects absent days.
    """
    records = get_admin_records(db, month=month, department_id=department_id, limit=50_000)

    present  = sum(1 for r in records if r["status"] == "Present")
    late     = sum(1 for r in records if r["status"] in ("Late", "Late & Early"))
    early    = sum(1 for r in records if r["status"] in ("Early", "Late & Early"))
    absent   = sum(1 for r in records if r["status"] == "Absent")
    leave    = sum(1 for r in records if r["status"] == "Leave")
    total    = len(records)
    attended = sum(1 for r in records if r["status"] in ("Present", "Late", "Early", "Late & Early"))
    rate     = round((attended / total) * 100, 2) if total else 0.0

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
        if r["status"] in ("Present", "Late", "Early", "Late & Early"):
            dept_map[did]["present"] += 1

    by_department = []
    for entry in dept_map.values():
        t = entry["total"]
        entry["rate"] = round((entry["present"] / t) * 100, 2) if t else 0.0
        by_department.append(entry)
    by_department.sort(key=lambda x: x.get("department_name") or "")

    return {
        "present":         present,
        "late":            late,
        "early":           early,
        "absent":          absent,
        "leave":           leave,
        "total_records":   total,
        "total_employees": len({r["employee_id"] for r in records}),
        "rate":            rate,
        "by_department":   by_department,
    }