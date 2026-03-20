from zk import ZK
from openpyxl import Workbook

# ---------------------------
# CONFIG
# ---------------------------
DEVICE_IP = "172.16.32.184"
DEVICE_PORT = 4370
TIMEOUT = 10

# ---------------------------
# Excel setup
# ---------------------------
wb = Workbook()
ws = wb.active
ws.title = "Employees"

# Only include fields that exist in zk.User
ws.append(["Employee ID", "Name", "Privilege", "Password"])

conn = None

try:
    zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=TIMEOUT)
    conn = zk.connect()
    conn.disable_device()

    # 🔹 Fetch all users
    users = conn.get_users()

    for user in users:
        ws.append([
            user.user_id,
            user.name,
            user.privilege,
            user.password
        ])

    conn.enable_device()

except Exception as e:
    print("❌ Error:", e)

finally:
    if conn:
        conn.disconnect()

file_name = "employee_list.xlsx"
wb.save(file_name)

print(f"✅ Employee list exported → {file_name}")
