# """
# ZKT Machine Connectivity Diagnostic Tool
# Helps identify and fix connection issues with ZKT attendance machines
# """
# import sys
# import socket
# import subprocess
# from pathlib import Path
# from datetime import datetime

# # Configuration
# DEVICE_IP = "172.16.32.184"
# DEVICE_PORT = 4370
# TIMEOUT = 5

# def test_ping():
#     """Test if device is reachable via ping"""
#     print("\n[1/5] 🔹 Testing PING Connectivity")
#     print("-" * 70)
    
#     try:
#         # Use ping command appropriate for the OS
#         if sys.platform == "win32":
#             result = subprocess.run(
#                 ["ping", "-n", "1", DEVICE_IP],
#                 capture_output=True,
#                 timeout=10
#             )
#         else:
#             result = subprocess.run(
#                 ["ping", "-c", "1", DEVICE_IP],
#                 capture_output=True,
#                 timeout=10
#             )
        
#         if result.returncode == 0:
#             print(f"✅ PING SUCCESSFUL - Device {DEVICE_IP} is reachable")
#             return True
#         else:
#             print(f"❌ PING FAILED - Device {DEVICE_IP} did not respond")
#             return False
#     except subprocess.TimeoutExpired:
#         print(f"❌ PING TIMEOUT - No response from {DEVICE_IP}")
#         return False
#     except FileNotFoundError:
#         print("⚠️  ping command not available - skipping this test")
#         return None
#     except Exception as e:
#         print(f"❌ PING ERROR: {str(e)}")
#         return False

# def test_socket_connection():
#     """Test raw socket connection to the port"""
#     print("\n[2/5] 🔹 Testing Socket Connection")
#     print("-" * 70)
    
#     try:
#         sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         sock.settimeout(TIMEOUT)
        
#         print(f"Attempting to connect to {DEVICE_IP}:{DEVICE_PORT} (timeout: {TIMEOUT}s)...")
#         result = sock.connect_ex((DEVICE_IP, DEVICE_PORT))
#         sock.close()
        
#         if result == 0:
#             print(f"✅ SOCKET CONNECTION SUCCESSFUL - Port {DEVICE_PORT} is open")
#             return True
#         else:
#             print(f"❌ SOCKET CONNECTION FAILED - Could not connect to port {DEVICE_PORT}")
#             print(f"   Error code: {result}")
#             return False
#     except socket.gaierror:
#         print(f"❌ HOSTNAME RESOLUTION FAILED - Invalid IP: {DEVICE_IP}")
#         return False
#     except socket.timeout:
#         print(f"❌ SOCKET TIMEOUT - No response on port {DEVICE_PORT}")
#         return False
#     except Exception as e:
#         print(f"❌ SOCKET ERROR: {str(e)}")
#         return False

# def test_pyzk_import():
#     """Test if pyzk library is installed"""
#     print("\n[3/5] 🔹 Testing pyzk Library")
#     print("-" * 70)
    
#     try:
#         from zk import ZK
#         print("✅ pyzk library is installed")
#         print(f"   ZK class: {ZK}")
#         return True
#     except ImportError as e:
#         print(f"❌ pyzk library not installed: {str(e)}")
#         print("   Fix: pip install pyzk")
#         return False
#     except Exception as e:
#         print(f"❌ Error importing pyzk: {str(e)}")
#         return False

# def test_zk_connection():
#     """Test actual ZK device connection using pyzk"""
#     print("\n[4/5] 🔹 Testing ZK Device Connection")
#     print("-" * 70)
    
#     try:
#         from zk import ZK
        
#         print(f"Creating ZK connection object...")
#         zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=TIMEOUT)
        
#         print(f"Attempting to connect to device...")
#         conn = zk.connect()
        
#         if conn:
#             print("✅ ZK DEVICE CONNECTION SUCCESSFUL")
#             print(f"   Connected to: {DEVICE_IP}:{DEVICE_PORT}")
            
#             # Try to get device info
#             try:
#                 conn.disable_device()
#                 print("   ✓ Device disabled for data fetch")
                
#                 users = conn.get_users()
#                 print(f"   ✓ Retrieved {len(users)} users from device")
                
#                 attendance = conn.get_attendance()
#                 print(f"   ✓ Retrieved {len(attendance)} attendance records")
                
#                 conn.enable_device()
#                 print("   ✓ Device re-enabled")
                
#                 conn.disconnect()
#                 return True
#             except Exception as e:
#                 print(f"   ⚠️  Connected but error fetching data: {str(e)}")
#                 try:
#                     conn.disconnect()
#                 except:
#                     pass
#                 return False
#         else:
#             print("❌ ZK device returned None connection")
#             return False
            
#     except socket.timeout:
#         print(f"❌ TIMEOUT - Device at {DEVICE_IP}:{DEVICE_PORT} not responding")
#         return False
#     except Exception as e:
#         print(f"❌ ZK CONNECTION ERROR: {str(e)}")
#         print(f"   Exception type: {type(e).__name__}")
#         return False

# def print_troubleshooting():
#     """Print troubleshooting guide"""
#     print("\n[5/5] 🔧 Troubleshooting Guide")
#     print("-" * 70)
    
#     print("""
# Common Issues and Solutions:

# 1. ❌ PING FAILED
#    → Device is not on the network or not reachable
#    Solutions:
#      - Verify IP address: 172.16.32.184 (check device screen)
#      - Check network cable is connected
#      - Check if device is powered on
#      - Check firewall rules allow this IP
#      - Try: ping 172.16.32.184

# 2. ❌ SOCKET CONNECTION FAILED (Port unreachable)
#    → Port 4370 might be wrong or device is not listening
#    Solutions:
#      - Verify port number: 4370 (check device documentation)
#      - Try alternative ports: 4370, 5200, 8080
#      - Check device network settings
#      - Restart the ZK device

# 3. ❌ ZK CONNECTION ERROR (timeout)
#    → Device exists but not responding to ZK protocol
#    Solutions:
#      - Device might be in a different network segment
#      - Check device firmware version compatibility
#      - Restart the device
#      - Check if device is accepting network connections

# 4. ✅ ALL TESTS PASS
#    → Connectivity is working!
#    → Check if employees exist on the device
#    → Check if attendance logs exist on the device
#    → Manually pull data using export script

# Configuration:
#    IP Address: 172.16.32.184
#    Port: 4370
#    Timeout: 5 seconds

# To change these, edit: app/background/zkt_connector.py or set environment variables
#     """)

# def main():
#     print("\n" + "="*70)
#     print("🔍 ZKT MACHINE CONNECTIVITY DIAGNOSTIC")
#     print("="*70)
#     print(f"\nDevice: {DEVICE_IP}:{DEVICE_PORT}")
#     print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
#     results = {}
    
#     # Run tests
#     results['ping'] = test_ping()
#     results['socket'] = test_socket_connection()
#     results['pyzk'] = test_pyzk_import()
    
#     if results['pyzk']:
#         results['zk'] = test_zk_connection()
#     else:
#         results['zk'] = None
#         print("\n[4/5] 🔹 Testing ZK Device Connection")
#         print("-" * 70)
#         print("⊘ SKIPPED - pyzk not installed")
    
#     print_troubleshooting()
    
#     # Summary
#     print("\n" + "="*70)
#     print("📊 SUMMARY")
#     print("="*70)
    
#     print("\nTest Results:")
#     print(f"  Ping:           {'✅ PASS' if results['ping'] else '❌ FAIL' if results['ping'] is False else '⊘ SKIP'}")
#     print(f"  Socket:         {'✅ PASS' if results['socket'] else '❌ FAIL'}")
#     print(f"  pyzk Library:   {'✅ PASS' if results['pyzk'] else '❌ FAIL'}")
#     print(f"  ZK Connection:  {'✅ PASS' if results['zk'] else '❌ FAIL' if results['zk'] is False else '⊘ SKIP'}")
    
#     all_passed = all(v for v in results.values() if v is not None)
    
#     if all_passed:
#         print("\n✅ ALL TESTS PASSED - Device is ready!")
#         return 0
#     else:
#         print("\n❌ SOME TESTS FAILED - See troubleshooting above")
#         return 1

# if __name__ == "__main__":
#     sys.exit(main())
