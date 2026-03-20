# """
# Debug script to test attendance data format and sync
# Helps identify input format errors
# """
# import sys
# from pathlib import Path
# from datetime import datetime, time, date

# # Add parent directory to path
# parent_dir = Path(__file__).parent.parent
# sys.path.insert(0, str(parent_dir))

# from app.background.zkt_connector import ZKTConnector
# from app.schemas.attendance import AttendanceCreate
# from app.models.attendance import AttendanceModeEnum
# import json

# # Configuration
# DEVICE_IP = "172.16.32.184"
# DEVICE_PORT = 4370
# TIMEOUT = 20

# def test_attendance_format():
#     """Test attendance data format validation"""
#     print("\n" + "="*70)
#     print("🔧 TESTING ATTENDANCE DATA FORMAT")
#     print("="*70)
    
#     # 1. Fetch records from device
#     print("\n[1/3] 🔹 Fetching records from ZKT device...")
#     connector = ZKTConnector(
#         machine_ip=DEVICE_IP,
#         machine_port=DEVICE_PORT,
#         timeout=TIMEOUT
#     )
    
#     records = connector.get_attendance_records()
    
#     if not records:
#         print("⚠️  No records found on device")
#         return False
    
#     print(f"✅ Fetched {len(records)} records")
    
#     # 2. Test format of first few records
#     print("\n[2/3] 🔹 Testing record format...")
#     print("-" * 70)
    
#     valid_count = 0
#     error_count = 0
    
#     for idx, record in enumerate(records[:5]):
#         print(f"\nRecord {idx + 1}:")
#         print(f"  Raw data: {json.dumps({k: str(v) for k, v in record.items()}, indent=4)}")
        
#         try:
#             # Validate field types
#             print(f"  ✓ employee_id: {record.get('employee_id')} (type: {type(record.get('employee_id')).__name__})")
#             print(f"  ✓ employee_name: {record.get('employee_name')} (type: {type(record.get('employee_name')).__name__})")
#             print(f"  ✓ attendance_date: {record.get('attendance_date')} (type: {type(record.get('attendance_date')).__name__})")
#             print(f"  ✓ attendance_time: {record.get('attendance_time')} (type: {type(record.get('attendance_time')).__name__})")
#             print(f"  ✓ punch: {record.get('punch')} (type: {type(record.get('punch')).__name__})")
#             print(f"  ✓ attendance_mode: {record.get('attendance_mode')} (type: {type(record.get('attendance_mode')).__name__})")
            
#             # Try to create AttendanceCreate object
#             mode_str = record.get("attendance_mode", "onsite")
#             if isinstance(mode_str, str):
#                 attendance_mode = AttendanceModeEnum(mode_str)
#             else:
#                 attendance_mode = mode_str
            
#             att = AttendanceCreate(
#                 employee_id=int(record.get("employee_id")),
#                 employee_name=str(record.get("employee_name", "Unknown")),
#                 attendance_date=record.get("attendance_date"),
#                 attendance_time=record.get("attendance_time"),
#                 punch=bool(record.get("punch")),
#                 attendance_mode=attendance_mode,
#             )
            
#             print(f"  ✅ VALID - Successfully created AttendanceCreate object")
#             valid_count += 1
            
#         except Exception as e:
#             print(f"  ❌ ERROR: {str(e)}")
#             error_count += 1
    
#     print("\n" + "-" * 70)
#     print(f"✅ Valid records: {valid_count}")
#     print(f"❌ Invalid records: {error_count}")
    
#     # 3. Summary
#     print("\n[3/3] 🔹 Summary")
#     print("-" * 70)
    
#     if error_count == 0:
#         print("✅ All records have correct format!")
#         print("ℹ️  Ready for database sync")
#         return True
#     else:
#         print("❌ Some records have format errors")
#         print("⚠️  Check the errors above and fix the ZKT connector")
#         return False

# if __name__ == "__main__":
#     try:
#         success = test_attendance_format()
#         sys.exit(0 if success else 1)
#     except Exception as e:
#         print(f"\n❌ Test failed: {str(e)}")
#         import traceback
#         traceback.print_exc()
#         sys.exit(1)
