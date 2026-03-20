from zk import ZK
from datetime import datetime
from openpyxl import Workbook
import json
import os

# ---------------------------
# CONFIG
# ---------------------------
DEVICE_IP = "172.16.32.184"
DEVICE_PORT = 4370
TIMEOUT = 20

SYNC_FILE = "last_sync.json"

# ---------------------------
# Load last sync time
# ---------------------------
def get_last_sync():
    if os.path.exists(SYNC_FILE):
        with open(SYNC_FILE) as f:
            data = json.load(f)
            return datetime.fromisoformat(data["last_sync"])
    return datetime(2000, 1, 1)  # first run

def save_last_sync(time):
    with open(SYNC_FILE, "w") as f:
        json.dump({"last_sync": time.isoformat()}, f)

# ---------------------------
# Excel Setup
# ---------------------------
wb = Workbook()
ws = wb.active
ws.append(["Employee ID", "Employee Name", "Date", "Time", "Punch"])

last_sync = get_last_sync()
print("🔹 Last Sync:", last_sync)

conn = None
newest_time = last_sync

try:
    zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=TIMEOUT)
    conn = zk.connect()

    conn.disable_device()

    # ---------------------------
    # Load users
    # ---------------------------
    users = conn.get_users()
    user_map = {str(u.user_id): u.name for u in users}

    print(f"✅ Loaded {len(user_map)} users")

    # ---------------------------
    # Fetch attendance logs
    # ---------------------------
    logs = conn.get_attendance()

    new_logs = 0

    for record in reversed(logs):

        ts = record.timestamp
        if not ts:
            continue

        # stop early if old record
        if ts <= last_sync:
            break

        user_id = str(record.user_id)
        name = user_map.get(user_id, "Unknown")

        ws.append([
            user_id,
            name,
            ts.strftime("%Y-%m-%d"),
            ts.strftime("%H:%M:%S"),
            "IN" if record.punch == 0 else "OUT"
        ])

        new_logs += 1

        if ts > newest_time:
            newest_time = ts

    conn.enable_device()

except Exception as e:
    print("❌ Error:", e)

finally:
    if conn:
        conn.disconnect()

# ---------------------------
# Save file
# ---------------------------
file_name = f"attendance_sync_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
wb.save(file_name)

print(f"✅ {new_logs} new logs exported")

# ---------------------------
# Update last sync
# ---------------------------
save_last_sync(newest_time)

print("🔹 New last sync:", newest_time)