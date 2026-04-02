from zk import ZK
from openpyxl import Workbook
from datetime import datetime

# ---------------------------
# CONFIG
# ---------------------------
DEVICE_IP = "172.16.32.184"
DEVICE_PORT = 4370
TIMEOUT = 20

# Date + Time filter
FROM_DATETIME = datetime.strptime("2026-03-27 00:00:00", "%Y-%m-%d %H:%M:%S")

# ---------------------------
# Excel setup
# ---------------------------
wb = Workbook()
ws = wb.active
ws.title = "Attendance"

ws.append(["Employee ID", "Employee Name", "Date", "Time", "Punch"])

conn = None

try:
    zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=TIMEOUT)
    conn = zk.connect()
    conn.disable_device()

    # Fetch users
    users = conn.get_users()
    user_map = {}

    for user in users:
        user_map[str(user.user_id)] = user.name

    print(f"✅ Loaded {len(user_map)} users")

    # Fetch attendance logs
    attendance = conn.get_attendance()

    for record in attendance:
        ts = record.timestamp
        if not ts:
            continue

        # Filter by date + time
        if ts < FROM_DATETIME:
            continue

        user_id = str(record.user_id)
        user_name = user_map.get(user_id, "Unknown")

        ws.append([
            user_id,
            user_name,
            ts.strftime("%Y-%m-%d"),
            ts.strftime("%I:%M:%S %p"),
            "IN" if record.punch == 0 else "OUT"
        ])

    conn.enable_device()

except Exception as e:
    print("❌ Error:", e)

finally:
    if conn:
        conn.disconnect()

file_name = f"attendance_from_{FROM_DATETIME.strftime('%Y%m%d_%H%M')}.xlsx"
wb.save(file_name)

print(f"✅ Attendance exported from {FROM_DATETIME} → {file_name}")