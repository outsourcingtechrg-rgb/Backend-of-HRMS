"""
attendance.py  –  CRUD + processing logic

═══════════════════════════════════════════════════════════════════
Model field reference
═══════════════════════════════════════════════════════════════════
  attendance_date  : Date
  attendance_time  : Time
  punch            : Boolean
                       False = CHECK-IN   (punch in)
                       True  = CHECK-OUT  (punch out)
  employee_id      : Integer   ← FK to employees table (DB id)

═══════════════════════════════════════════════════════════════════
Core pairing logic
═══════════════════════════════════════════════════════════════════
The ZKT machine writes one raw row per punch event.
We convert those raw rows into logical AttendanceRecord dicts:

  ONE logical record  =  one IN punch  +  its matching OUT punch

Pairing rules
─────────────
1. Separate all punches into IN bucket (punch=False) and OUT
   bucket (punch=True), sorted chronologically by datetime.

2. For each IN punch, find the nearest OUT punch that occurs
   AFTER it, within the allowed window:

     Day  shift  →  window = [ in_datetime,  in_datetime + 14 h )
     Night shift →  window = [ in_datetime,  in_datetime + 16 h )

   "nearest" = smallest positive gap wins (greedy, left-to-right).

3. The logical record is dated on the IN punch date.
   This means a night-shift employee who clocks in on 12 Mar at
   21:00 and clocks out on 13 Mar at 05:00 gets ONE record:
       date    = 2026-03-12   ← IN date
       in_time = 21:00
       out_time= 05:00        ← from the next calendar day
       hours   = 8.0

4. For the 13 Mar shift that starts at 21:00, the IN punch on
   13 Mar at 21:00 is paired separately → date = 2026-03-13.

5. Orphan OUT punch (no matching IN): kept as a record with
   in_time=None so it is visible to HR but does not inflate hours.

═══════════════════════════════════════════════════════════════════
Status rules
═══════════════════════════════════════════════════════════════════
  Absent  : no IN punch
  Late    : IN punch  >  shift.shift_late_on   (if shift provided)
            IN punch  >  shift.shift_start + 15 min  (grace period)
            IN punch  >  09:15                (fallback, no shift)
  Present : IN punch on time
"""

from sqlalchemy.orm import Session
from datetime import date, datetime, time, timedelta
from typing import List, Optional
from calendar import monthrange

from app.models.attendance import Attendance
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate


# ═══════════════════════════════════════════════════════════════════
# BASIC CRUD  (raw punch rows – unchanged from original)
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


def update_attendance(
    db: Session,
    attendance_id: int,
    data: AttendanceUpdate,
) -> Optional[Attendance]:
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
    employee_id: int = None,
    attendance_date: date = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Attendance]:
    q = db.query(Attendance)
    if employee_id:
        q = q.filter(Attendance.employee_id == employee_id)
    if attendance_date:
        q = q.filter(Attendance.attendance_date == attendance_date)
    return q.offset(skip).limit(limit).all()


def get_attendance_by_employee_and_date(
    db: Session,
    employee_id: int,
    attendance_date: date,
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
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════

def _to_mins(t: Optional[time]) -> Optional[int]:
    """time → minutes from midnight.  None-safe."""
    return (t.hour * 60 + t.minute) if t else None


def _is_overnight(shift) -> bool:
    """
    True when shift_end < shift_start (wraps past midnight).
    e.g.  start=21:00 (1260 min),  end=05:00 (300 min)  → overnight.
    """
    if shift is None:
        return False
    s = _to_mins(shift.shift_start_timing)
    e = _to_mins(shift.shift_end_timing)
    return s is not None and e is not None and e < s


def _late_threshold(shift) -> time:
    """
    Return the time after which a check-in is considered Late.
    Priority:
      1. shift.shift_late_on          (explicitly configured)
      2. shift.shift_start + 15 min   (grace period fallback)
      3. 09:15                         (no shift info)
    """
    if shift and shift.shift_late_on:
        return shift.shift_late_on

    if shift and shift.shift_start_timing:
        grace = _to_mins(shift.shift_start_timing) + 15
        return time(grace // 60 % 24, grace % 60)

    return time(9, 15)


def _get_shift(db: Session, employee_id: int):
    """
    Load the Shift assigned to this employee (via the Employee ORM relation).
    Returns None if the employee has no shift or the relation is unavailable.
    """
    try:
        from app.models.employee import Employee
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        return emp.shift if emp else None
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════
# CORE PROCESSING
# Converts raw Attendance rows → AttendanceRecord dicts
# ═══════════════════════════════════════════════════════════════════

def _build_records(
    punches: List[Attendance],
    shift=None,
) -> List[dict]:
    """
    Parameters
    ----------
    punches : raw Attendance ORM rows (may span multiple calendar dates)
    shift   : optional Shift ORM object for late-detection and window sizing

    Returns
    -------
    List of AttendanceRecord dicts, sorted most-recent first.
    Each record is dated on the IN punch date (not the OUT punch date).
    """
    if not punches:
        return []

    overnight  = _is_overnight(shift)
    threshold  = _late_threshold(shift)

    # ── 1. Split into IN / OUT buckets ────────────────────────────────
    ins:  List[Attendance] = [p for p in punches if p.punch is False]
    outs: List[Attendance] = [p for p in punches if p.punch is True]

    # Sort by full datetime so cross-midnight order is correct
    key = lambda p: datetime.combine(p.attendance_date, p.attendance_time)
    ins.sort(key=key)
    outs.sort(key=key)

    # ── 2. Pair each IN with the nearest subsequent OUT ────────────────
    #
    # Max pairing window:
    #   Night shift: 16 h  (allows a bit of overtime)
    #   Day   shift: 14 h
    #
    # "The attendance_date for a logical record = IN punch date."
    # OUT punch may be on the NEXT calendar date for overnight shifts.
    max_gap_sec = (16 if overnight else 14) * 3600

    used_out: set = set()
    pairs: List[tuple] = []   # (in_punch | None, out_punch | None)

    for inp in ins:
        in_dt      = datetime.combine(inp.attendance_date, inp.attendance_time)
        best_out   = None
        best_delta = None

        for outp in outs:
            if id(outp) in used_out:
                continue

            out_dt = datetime.combine(outp.attendance_date, outp.attendance_time)
            delta  = (out_dt - in_dt).total_seconds()

            # OUT must come AFTER IN, within the window
            if delta <= 0 or delta > max_gap_sec:
                continue

            if best_delta is None or delta < best_delta:
                best_out, best_delta = outp, delta

        pairs.append((inp, best_out))
        if best_out is not None:
            used_out.add(id(best_out))

    # Orphan OUTs (employee forgot to punch in – keep for visibility)
    for outp in outs:
        if id(outp) not in used_out:
            pairs.append((None, outp))

    # ── 3. Build one AttendanceRecord dict per pair ────────────────────
    result: List[dict] = []

    for inp, outp in pairs:
        anchor = inp or outp   # prefer IN for record date

        in_time   = inp.attendance_time  if inp  else None
        out_time  = outp.attendance_time if outp else None
        in_date   = inp.attendance_date  if inp  else None
        out_date  = outp.attendance_date if outp else None

        # Record is keyed on the IN date (even for overnight)
        record_date = in_date or out_date

        # ── Hours (cross-midnight safe) ──────────────────────────────
        hours: Optional[float] = None
        if in_time and out_time and in_date and out_date:
            dt_in  = datetime.combine(in_date,  in_time)
            dt_out = datetime.combine(out_date, out_time)
            secs   = (dt_out - dt_in).total_seconds()
            if secs > 0:
                hours = round(secs / 3600, 2)

        # ── Status ─────────────────────────────────────────────────
        if in_time is None:
            status = "Absent"
        elif in_time > threshold:
            status = "Late"
        else:
            status = "Present"

        result.append({
            "id":          anchor.id,
            "employee_id": anchor.employee_id,
            "date":        str(record_date),
            "status":      status,
            "in_time":     in_time.strftime("%H:%M")  if in_time  else None,
            "out_time":    out_time.strftime("%H:%M") if out_time else None,
            "hours":       hours,
            "note":        None,
        })

    # Most recent first
    return sorted(result, key=lambda x: x["date"], reverse=True)


# ═══════════════════════════════════════════════════════════════════
# USER-FACING  /me  ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

def get_my_attendance(
    db: Session,
    employee_id: int,
    month: Optional[str] = None,
) -> List[dict]:
    """
    Full attendance history for one employee.

    For overnight shifts the date window is padded by ±1 day so that the
    OUT punch on the first day of the next month (or last day of the
    previous month) is included and can be paired correctly.

    The returned records are then filtered back to the requested month
    using the IN-punch date (record["date"]).
    """
    shift     = _get_shift(db, employee_id)
    overnight = _is_overnight(shift)

    q = db.query(Attendance).filter(Attendance.employee_id == employee_id)

    if month:
        year, mon  = map(int, month.split("-"))
        last_day   = monthrange(year, mon)[1]
        start_date = date(year, mon, 1)
        end_date   = date(year, mon, last_day)

        # Pad by one day on each side for overnight so the OUT punch
        # on the adjacent month boundary is fetched and can be paired.
        if overnight:
            start_date -= timedelta(days=1)
            end_date   += timedelta(days=1)

        q = q.filter(Attendance.attendance_date.between(start_date, end_date))

    raw     = q.all()
    records = _build_records(raw, shift=shift)

    # Filter back to the requested month (using IN-punch date)
    if month:
        year, mon = map(int, month.split("-"))
        prefix = f"{year}-{mon:02d}"
        records = [r for r in records if r["date"].startswith(prefix)]

    return records


def get_today_attendance(
    db: Session,
    employee_id: int,
) -> Optional[dict]:
    """
    Return the currently-active attendance record for one employee.

    ┌─────────────────────────────────────────────────────────────┐
    │  Day shift  (e.g. 09:00 → 18:00)                           │
    │    Fetch today's punches only.                              │
    │    Return None if current time is past the shift end.       │
    ├─────────────────────────────────────────────────────────────┤
    │  Night shift  (e.g. 21:00 → 05:00)                         │
    │                                                             │
    │  PRE-MIDNIGHT window   21:00 – 23:59                        │
    │    Fetch today's punches.                                   │
    │    IN punch exists; OUT punch will come tomorrow.           │
    │                                                             │
    │  POST-MIDNIGHT window  00:00 – 05:00                        │
    │    The IN punch is on YESTERDAY's date.                     │
    │    The OUT punch may be on TODAY's date (or not yet made).  │
    │    Fetch yesterday + today; _build_records pairs them.      │
    │                                                             │
    │  OFF-SHIFT window       05:00 – 21:00                       │
    │    Return None.                                             │
    └─────────────────────────────────────────────────────────────┘
    """
    shift     = _get_shift(db, employee_id)
    overnight = _is_overnight(shift)

    now       = datetime.now()
    today     = now.date()
    yesterday = today - timedelta(days=1)
    now_mins  = now.hour * 60 + now.minute

    # ── No shift info → simple today-only fetch ──────────────────────
    if shift is None:
        raw   = db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.attendance_date == today,
        ).all()
        built = _build_records(raw, shift=None)
        return built[0] if built else None

    start_mins = _to_mins(shift.shift_start_timing)
    end_mins   = _to_mins(shift.shift_end_timing)

    # ── DAY shift ────────────────────────────────────────────────────
    if not overnight:
        # Outside shift window → nothing to show
        if now_mins > end_mins:
            return None

        raw   = db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.attendance_date == today,
        ).all()
        built = _build_records(raw, shift=shift)
        return built[0] if built else None

    # ── NIGHT (overnight) shift ──────────────────────────────────────

    # POST-MIDNIGHT:  00:00 → shift_end   (e.g. 00:00 – 05:00)
    if now_mins < end_mins:
        # IN punch is on yesterday; OUT punch may be on today
        raw = db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.attendance_date.in_([yesterday, today]),
        ).all()
        built = _build_records(raw, shift=shift)
        # _build_records dates the record on the IN date (yesterday)
        return built[0] if built else None

    # PRE-MIDNIGHT:  shift_start → 23:59  (e.g. 21:00 – 23:59)
    if now_mins >= start_mins:
        raw = db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.attendance_date == today,
        ).all()
        built = _build_records(raw, shift=shift)
        return built[0] if built else None

    # OFF-SHIFT window: after shift_end but before shift_start
    return None


def get_attendance_summary(
    db: Session,
    employee_id: int,
    month: str,
) -> dict:
    """Monthly summary – re-uses get_my_attendance for consistent logic."""
    records    = get_my_attendance(db, employee_id, month=month)
    present    = sum(1 for r in records if r["status"] == "Present")
    late       = sum(1 for r in records if r["status"] == "Late")
    absent     = sum(1 for r in records if r["status"] == "Absent")
    leave      = sum(1 for r in records if r["status"] == "Leave")
    total_days = len(records)
    rate       = round(((present + late) / total_days) * 100, 2) if total_days else 0

    return {
        "present":    present,
        "late":       late,
        "absent":     absent,
        "leave":      leave,
        "total_days": total_days,
        "rate":       rate,
    }