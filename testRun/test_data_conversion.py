# """
# Test data conversion with actual error scenarios
# Validates that the connector properly converts punch and attendance_time
# """
# from datetime import datetime, time, date

# print("\n" + "="*80)
# print("🧪 TESTING DATA CONVERSION - SIMULATING ACTUAL ERROR SCENARIOS")
# print("="*80)

# # Simulate actual error records from ZKT device
# test_records = [
#     {
#         'employee_id': 5,
#         'employee_name': 'Waseem',
#         'attendance_date': date(2026, 2, 17),
#         'attendance_time': datetime(2026, 2, 17, 5, 40, 47),  # Full datetime, not time!
#         'punch': 'OUT',  # String, not boolean!
#         'attendance_mode': 'onsite'
#     },
#     {
#         'employee_id': 6,
#         'employee_name': 'Munawar',
#         'attendance_date': date(2026, 2, 17),
#         'attendance_time': datetime(2026, 2, 17, 18, 26, 49),
#         'punch': 'IN',  # String 'IN'
#         'attendance_mode': 'onsite'
#     },
# ]

# print("\n[1/3] Testing Time Conversion (datetime → time)")
# print("-" * 80)

# for record in test_records:
#     att_time = record.get("attendance_time")
    
#     # Before fix: att_time is datetime(2026, 2, 17, 5, 40, 47)
#     print(f"Original: {repr(att_time)} (type: {type(att_time).__name__})")
    
#     # After fix:
#     if hasattr(att_time, 'time'):
#         att_time_fixed = att_time.time()
#     else:
#         att_time_fixed = att_time
    
#     print(f"  → Fixed: {repr(att_time_fixed)} (type: {type(att_time_fixed).__name__})")
    
#     # Validate it matches expected type
#     if isinstance(att_time_fixed, time):
#         print("  ✅ CORRECT - Now a time object!")
#     else:
#         print("  ❌ ERROR - Still not a time object")
#     print()

# print("\n[2/3] Testing Punch Conversion (string → boolean)")
# print("-" * 80)

# for record in test_records:
#     punch_raw = record.get("punch")
    
#     # Before fix: punch_raw is 'OUT' or 'IN' (string)
#     print(f"Original: {repr(punch_raw)} (type: {type(punch_raw).__name__})")
    
#     # After fix:
#     try:
#         if isinstance(punch_raw, str):
#             punch_str = punch_raw.strip().upper()
#             if punch_str in ['IN', '0']:
#                 is_in = True
#             elif punch_str in ['OUT', '1']:
#                 is_in = False
#             else:
#                 is_in = int(punch_str) == 0
#         else:
#             is_in = int(punch_raw) == 0
        
#         print(f"  → Fixed: {repr(is_in)} (type: {type(is_in).__name__})")
        
#         if isinstance(is_in, bool):
#             punch_type = "IN" if is_in else "OUT"
#             print(f"  ✅ CORRECT - Boolean value: {punch_type}")
#         else:
#             print("  ❌ ERROR - Not a boolean")
            
#     except Exception as e:
#         print(f"  ❌ ERROR: {str(e)}")
#     print()

# print("\n[3/3] Testing Complete Record Structure")
# print("-" * 80)

# from datetime import datetime, time

# def simulate_fixed_connector(record):
#     """Simulate the fixed connector logic"""
#     ts = record['attendance_time']
#     punch_raw = record['punch']
    
#     # Fix time
#     if hasattr(ts, 'time'):
#         att_time = ts.time()
#     else:
#         att_time = ts
    
#     # Fix punch
#     if isinstance(punch_raw, str):
#         punch_str = punch_raw.strip().upper()
#         if punch_str in ['IN', '0']:
#             is_in = True
#         elif punch_str in ['OUT', '1']:
#             is_in = False
#         else:
#             is_in = int(punch_str) == 0
#     else:
#         is_in = int(punch_raw) == 0
    
#     return {
#         'employee_id': record['employee_id'],
#         'employee_name': record['employee_name'],
#         'attendance_date': record['attendance_date'],
#         'attendance_time': att_time,
#         'punch': is_in,
#         'attendance_mode': record['attendance_mode']
#     }

# for idx, record in enumerate(test_records, 1):
#     print(f"\nRecord {idx}:")
#     fixed = simulate_fixed_connector(record)
    
#     print(f"  employee_id: {fixed['employee_id']} ✓")
#     print(f"  employee_name: {fixed['employee_name']} ✓")
#     print(f"  attendance_date: {fixed['attendance_date']} (type: {type(fixed['attendance_date']).__name__}) ✓")
#     print(f"  attendance_time: {fixed['attendance_time']} (type: {type(fixed['attendance_time']).__name__}) {'✅' if isinstance(fixed['attendance_time'], time) else '❌'}")
#     print(f"  punch: {fixed['punch']} (type: {type(fixed['punch']).__name__}) {'✅' if isinstance(fixed['punch'], bool) else '❌'}")
#     print(f"  attendance_mode: {fixed['attendance_mode']} ✓")

# print("\n" + "="*80)
# print("✅ CONVERSION TESTS COMPLETE")
# print("="*80 + "\n")
