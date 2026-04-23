#!/usr/bin/env python3
"""
Test the leave API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1/leaves"

def test_types():
    """Test get leave types"""
    try:
        response = requests.get(f"{BASE_URL}/types?skip=0&limit=100")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success! Found {len(data)} leave types")
            for lt in data[:3]:
                print(f"  - {lt.get('name')} (ID: {lt.get('id')})")
        else:
            print(f"✗ Error: {response.text}")
    except Exception as e:
        print(f"✗ Exception: {e}")

if __name__ == "__main__":
    test_types()
