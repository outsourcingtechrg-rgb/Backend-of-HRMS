#!/usr/bin/env python3
"""
Leave Management API - Test Examples
Run these examples to test the implementation
"""

import requests
import json
from datetime import date, timedelta

BASE_URL = "http://localhost:8000/api/v1"
HEADERS = {"Content-Type": "application/json"}

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg):
    print(f"{YELLOW}→ {msg}{RESET}")

def test_leave_types():
    """Test Leave Type endpoints"""
    print(f"\n{YELLOW}Testing Leave Types{RESET}")
    print("=" * 50)
    
    # Create Casual Leave
    print_info("Creating Casual Leave type...")
    data = {
        "name": "Casual Leave",
        "code": "CL",
        "description": "Casual leave for personal reasons",
        "days_per_year": 12,
        "carry_forward": True,
        "max_carry_forward": 5,
        "is_active": True,
        "is_paid": True,
        "reset_month": 1
    }
    resp = requests.post(f"{BASE_URL}/leaves/types", json=data, headers=HEADERS)
    if resp.status_code == 201:
        cl_data = resp.json()
        casual_leave_id = cl_data['id']
        print_success(f"Casual Leave created (ID: {casual_leave_id})")
    else:
        print_error(f"Failed to create: {resp.text}")
        return None
    
    # Create Sick Leave
    print_info("Creating Sick Leave type...")
    data = {
        "name": "Sick Leave",
        "code": "SL",
        "description": "Sick leave - requires medical certificate",
        "days_per_year": 10,
        "carry_forward": False,
        "is_active": True,
        "is_paid": True,
        "requires_document": True,
        "reset_month": 1
    }
    resp = requests.post(f"{BASE_URL}/leaves/types", json=data, headers=HEADERS)
    if resp.status_code == 201:
        sl_data = resp.json()
        sick_leave_id = sl_data['id']
        print_success(f"Sick Leave created (ID: {sick_leave_id})")
    else:
        print_error(f"Failed to create: {resp.text}")
        return None
    
    # Get all leave types
    print_info("Fetching all leave types...")
    resp = requests.get(f"{BASE_URL}/leaves/types", headers=HEADERS)
    if resp.status_code == 200:
        types_list = resp.json()
        print_success(f"Found {len(types_list)} leave types")
        for lt in types_list:
            print(f"  - {lt['name']} ({lt['code']}): {lt['days_per_year']} days/year")
    else:
        print_error(f"Failed to fetch: {resp.text}")
    
    return {"casual_leave_id": casual_leave_id, "sick_leave_id": sick_leave_id}

def test_leave_allocations(leave_types):
    """Test Leave Allocation endpoints"""
    print(f"\n{YELLOW}Testing Leave Allocations{RESET}")
    print("=" * 50)
    
    if not leave_types:
        print_error("Skipping - no leave types available")
        return None
    
    casual_leave_id = leave_types['casual_leave_id']
    sick_leave_id = leave_types['sick_leave_id']
    
    # Allocate Casual Leave to Employee 1
    print_info("Creating allocation: Employee 1 - 12 days of Casual Leave (2024)...")
    data = {
        "employee_id": 1,
        "leave_type_id": casual_leave_id,
        "year": 2024,
        "allocated_days": 12,
        "used_days": 0,
        "carried_forward": 2
    }
    resp = requests.post(f"{BASE_URL}/leaves/allocations", json=data, headers=HEADERS)
    if resp.status_code == 201:
        alloc_data = resp.json()
        allocation_id = alloc_data['id']
        print_success(f"Allocation created (ID: {allocation_id})")
        print(f"  Available: {alloc_data.get('allocated_days', 0)} + {alloc_data.get('carried_forward', 0)} = {alloc_data.get('allocated_days', 0) + alloc_data.get('carried_forward', 0)} days")
    else:
        print_error(f"Failed to create: {resp.text}")
        return None
    
    # Allocate Sick Leave
    print_info("Creating allocation: Employee 1 - 10 days of Sick Leave (2024)...")
    data = {
        "employee_id": 1,
        "leave_type_id": sick_leave_id,
        "year": 2024,
        "allocated_days": 10,
        "used_days": 0,
        "carried_forward": 0
    }
    resp = requests.post(f"{BASE_URL}/leaves/allocations", json=data, headers=HEADERS)
    if resp.status_code == 201:
        print_success("Sick Leave allocation created")
    else:
        print_error(f"Failed: {resp.text}")
    
    # Get employee balance
    print_info("Fetching Employee 1 leave balance for 2024...")
    resp = requests.get(f"{BASE_URL}/leaves/employees/1/balance?year=2024", headers=HEADERS)
    if resp.status_code == 200:
        balance = resp.json()
        print_success(f"Balance retrieved:")
        for b in balance['balances']:
            print(f"  {b['leave_type_name']}: {b['allocated_days']}+{b['carried_forward']}-{b['used_days']}={b['available_days']} days")
    else:
        print_error(f"Failed: {resp.text}")
    
    return {"allocation_id": allocation_id, "casual_leave_id": casual_leave_id}

def test_leave_requests(allocations):
    """Test Leave Request endpoints"""
    print(f"\n{YELLOW}Testing Leave Requests{RESET}")
    print("=" * 50)
    
    if not allocations:
        print_error("Skipping - no allocations available")
        return None
    
    casual_leave_id = allocations['casual_leave_id']
    
    # Submit leave request
    print_info("Employee 1 submitting leave request: 5 days of Casual Leave...")
    start_date = date.today() + timedelta(days=5)
    end_date = start_date + timedelta(days=4)
    data = {
        "employee_id": 1,
        "leave_type_id": casual_leave_id,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "days": 5,
        "reason": "Planned vacation"
    }
    resp = requests.post(f"{BASE_URL}/leaves/requests", json=data, headers=HEADERS)
    if resp.status_code == 201:
        request_data = resp.json()
        request_id = request_data['id']
        print_success(f"Leave request submitted (ID: {request_id}, Status: {request_data['status']})")
    else:
        print_error(f"Failed: {resp.text}")
        return None
    
    # Get pending requests
    print_info("Fetching all pending leave requests...")
    resp = requests.get(f"{BASE_URL}/leaves/requests", headers=HEADERS)
    if resp.status_code == 200:
        requests_list = resp.json()
        print_success(f"Found {len(requests_list)} pending request(s)")
        for req in requests_list:
            print(f"  - ID {req['id']}: Employee {req['employee_id']}, {req['days']} days, Status: {req['status']}")
    else:
        print_error(f"Failed: {resp.text}")
    
    return {"request_id": request_id}

def test_approval_workflow(request_info):
    """Test Leave Request Approval Workflow"""
    print(f"\n{YELLOW}Testing Approval Workflow{RESET}")
    print("=" * 50)
    
    if not request_info:
        print_error("Skipping - no request available")
        return
    
    request_id = request_info['request_id']
    
    # Check balance before approval
    print_info("Checking Employee 1 balance BEFORE approval...")
    resp = requests.get(f"{BASE_URL}/leaves/employees/1/balance?year=2024", headers=HEADERS)
    if resp.status_code == 200:
        balance = resp.json()
        for b in balance['balances']:
            if b['leaf_type_name'] or True:  # Just print all
                print(f"  Available: {b['available_days']} days")
    
    # Approve request
    print_info(f"Manager approving request {request_id}...")
    data = {"action_by": 5}  # Manager ID
    resp = requests.post(f"{BASE_URL}/leaves/requests/{request_id}/approve", json=data, headers=HEADERS)
    if resp.status_code == 200:
        print_success(f"Request approved! Status: {resp.json()['status']}")
    else:
        print_error(f"Failed: {resp.text}")
        return
    
    # Check balance after approval
    print_info("Checking Employee 1 balance AFTER approval...")
    resp = requests.get(f"{BASE_URL}/leaves/employees/1/balance?year=2024", headers=HEADERS)
    if resp.status_code == 200:
        balance = resp.json()
        for b in balance['balances']:
            print(f"  Available: {b['available_days']} days (should be reduced by 5)")
    
    # View transactions
    print_info("Viewing leave transactions...")
    resp = requests.get(f"{BASE_URL}/leaves/employees/1/transactions", headers=HEADERS)
    if resp.status_code == 200:
        transactions = resp.json()
        print_success(f"Found {len(transactions)} transaction(s)")
        for t in transactions:
            print(f"  - Type: {t['type']}, Days: {t['days']}")
    
    return request_id

def test_cancellation_workflow(request_id):
    """Test Leave Request Cancellation"""
    print(f"\n{YELLOW}Testing Cancellation Workflow{RESET}")
    print("=" * 50)
    
    if not request_id:
        print_error("Skipping - no approved request available")
        return
    
    # Cancel the approved request
    print_info(f"Cancelling approved request {request_id}...")
    resp = requests.post(f"{BASE_URL}/leaves/requests/{request_id}/cancel?canceller_id=1", headers=HEADERS)
    if resp.status_code == 200:
        print_success(f"Request cancelled! Status: {resp.json()['status']}")
    else:
        print_error(f"Failed: {resp.text}")
        return
    
    # Check balance after cancellation
    print_info("Checking Employee 1 balance AFTER cancellation...")
    resp = requests.get(f"{BASE_URL}/leaves/employees/1/balance?year=2024", headers=HEADERS)
    if resp.status_code == 200:
        balance = resp.json()
        for b in balance['balances']:
            print(f"  Available: {b['available_days']} days (should be restored)")
    
    # View transactions again
    print_info("Viewing leave transactions (should show deduction + reversal)...")
    resp = requests.get(f"{BASE_URL}/leaves/employees/1/transactions", headers=HEADERS)
    if resp.status_code == 200:
        transactions = resp.json()
        print_success(f"Found {len(transactions)} transaction(s)")
        for t in transactions:
            print(f"  - Type: {t['type']}, Days: {t['days']}")

def test_insufficient_balance():
    """Test Insufficient Balance Scenario"""
    print(f"\n{YELLOW}Testing Insufficient Balance Error{RESET}")
    print("=" * 50)
    
    # Try to request more days than available
    print_info("Attempting to request 100 days (should fail with insufficient balance)...")
    start_date = date.today() + timedelta(days=5)
    data = {
        "employee_id": 1,
        "leave_type_id": 1,
        "start_date": str(start_date),
        "end_date": str(start_date + timedelta(days=99)),
        "days": 100,
        "reason": "Way too much leave"
    }
    resp = requests.post(f"{BASE_URL}/leaves/requests", json=data, headers=HEADERS)
    if resp.status_code == 400:
        print_success(f"Correctly rejected: {resp.json()['detail']}")
    else:
        print_error(f"Should have failed but got {resp.status_code}")

def main():
    """Run all tests"""
    print(f"\n{YELLOW}{'='*50}")
    print(f"Leave Management API - Test Suite")
    print(f"{'='*50}{RESET}")
    
    # Test leave types
    leave_types = test_leave_types()
    
    # Test allocations
    allocations = test_leave_allocations(leave_types)
    
    # Test requests
    request_info = test_leave_requests(allocations)
    
    # Test approval workflow
    approved_request_id = test_approval_workflow(request_info)
    
    # Test cancellation
    test_cancellation_workflow(approved_request_id)
    
    # Test error handling
    test_insufficient_balance()
    
    print(f"\n{YELLOW}{'='*50}")
    print(f"Test Suite Completed!")
    print(f"{'='*50}{RESET}\n")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API. Make sure the server is running at http://localhost:8000")
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
