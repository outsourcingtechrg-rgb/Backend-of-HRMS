from zk import ZK
from datetime import datetime


def fetch_attendance(device_ip: str, port: int, from_date: str, from_time: str):

    timeout = 20
    conn = None
    data = []

    from_datetime = datetime.strptime(
        f"{from_date} {from_time}", "%Y-%m-%d %H:%M:%S"
    )

    try:
        zk = ZK(device_ip, port=port, timeout=timeout)
        conn = zk.connect()
        conn.disable_device()

        # Load users
        users = conn.get_users()
        user_map = {str(u.user_id): u.name for u in users}

        # Fetch logs
        attendance = conn.get_attendance()

        # Reverse to start from newest logs
        for record in reversed(attendance):

            ts = record.timestamp
            if not ts:
                continue

            # Stop early when older logs appear
            if ts < from_datetime:
                break

            uid = str(record.user_id)

            data.append({
                "employee_id": uid,
                "employee_name": user_map.get(uid, "Unknown"),
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "punch": "IN" if record.punch == 0 else "OUT"
            })

        conn.enable_device()

    except Exception as e:
        print("Error:", e)

    finally:
        if conn:
            conn.disconnect()

    return data

records = fetch_attendance(
    device_ip="172.16.32.184",
    port=4370,
    from_date="2026-03-09",
    from_time="21:00:00"
)

print("Total Records:", len(records))
print("all records:", records)