#!/usr/bin/env python3
"""
Test script to diagnose farmer API connection issues.
"""
import requests
import sys

# Configuration from database
API_BASE_URL = "https://jockstrap-boxlike-revisable.ngrok-free.dev"
API_KEY = "961424ec-94b1-4a00-b9a0-04d948ebd60c"
HIVE_IDS = [
    "814a8709-a39d-452a-a1fb-1d61c05f803c",
    "e2d3a1ac-ac5e-4dc0-9988-9dbe8a79cfcd",
    "4e4c85c5-4a3c-4a1f-ad31-6068e8f8da1b"
]

def test_health():
    """Test the health endpoint."""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False

def test_recordings_no_auth():
    """Test recordings endpoint without authentication."""
    print("\nTesting recordings endpoint without auth...")
    try:
        response = requests.get(f"{API_BASE_URL}/recordings", timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")
    except Exception as e:
        print(f"  Error: {e}")

def test_recordings_with_auth(header_name="X-API-Key"):
    """Test recordings endpoint with authentication."""
    print(f"\nTesting recordings endpoint with {header_name} header...")
    try:
        headers = {header_name: API_KEY}
        response = requests.get(f"{API_BASE_URL}/recordings", headers=headers, timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Found {len(data.get('recordings', []))} recordings")
            if data.get('recordings'):
                print(f"  First few: {data['recordings'][:3]}")
    except Exception as e:
        print(f"  Error: {e}")

def test_recordings_with_hive_filter(hive_id, header_name="X-API-Key"):
    """Test recordings endpoint with hive_id filter."""
    print(f"\nTesting recordings for hive {hive_id}...")
    try:
        headers = {header_name: API_KEY}
        response = requests.get(
            f"{API_BASE_URL}/recordings",
            headers=headers,
            params={"hive_id": hive_id},
            timeout=10
        )
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Farmer API Connection Test")
    print("=" * 60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"API Key: {API_KEY}")
    print("=" * 60)
    
    # Test health
    if not test_health():
        print("\nHealth check failed. Server may be down.")
        sys.exit(1)
    
    # Test without auth
    test_recordings_no_auth()
    
    # Test with different header cases
    test_recordings_with_auth("X-API-Key")
    test_recordings_with_auth("x-api-key")
    test_recordings_with_auth("X-Api-Key")
    
    # Test with hive filters
    for hive_id in HIVE_IDS:
        test_recordings_with_hive_filter(hive_id, "X-API-Key")
    
    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)
