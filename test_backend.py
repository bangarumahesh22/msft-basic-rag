"""
Simple test script to verify the backend API is working
Run this after starting the backend: python src/BE/main.py
"""

import requests
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BACKEND_HOST = os.getenv("BACKEND_HOST", "localhost")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Backend is running")
            print(f"    - Search configured: {data.get('search_configured')}")
            print(f"    - OpenAI configured: {data.get('openai_configured')}")
            return True
        else:
            print(f"  ✗ Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Cannot connect to backend at {BACKEND_URL}")
        print("    Make sure the backend is running: python src/BE/main.py")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_query_endpoint():
    """Test the query endpoint"""
    print("\nTesting query endpoint...")
    
    test_query = {
        "query": "What is Azure AI Search?",
        "session_id": "test_session",
        "max_results": 3
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/query",
            json=test_query,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Query endpoint working")
            print(f"    - Answer length: {len(data.get('answer', ''))} characters")
            print(f"    - Sources found: {len(data.get('sources', []))}")
            print(f"    - Session ID: {data.get('session_id')}")
            return True
        else:
            print(f"  ✗ Query failed with status {response.status_code}")
            print(f"    Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_conversation_endpoints():
    """Test conversation management endpoints"""
    print("\nTesting conversation endpoints...")
    
    session_id = "test_session"
    
    try:
        # Get conversation
        response = requests.get(f"{BACKEND_URL}/conversation/{session_id}", timeout=5)
        if response.status_code == 200:
            print(f"  ✓ Get conversation endpoint working")
        else:
            print(f"  ✗ Get conversation failed with status {response.status_code}")
            return False
        
        # Clear conversation
        response = requests.delete(f"{BACKEND_URL}/conversation/{session_id}", timeout=5)
        if response.status_code == 200:
            print(f"  ✓ Clear conversation endpoint working")
            return True
        else:
            print(f"  ✗ Clear conversation failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("BACKEND API TEST SUITE")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health_check()))
    results.append(("Query Endpoint", test_query_endpoint()))
    results.append(("Conversation Endpoints", test_conversation_endpoints()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        print("\nTroubleshooting:")
        print("1. Make sure the backend is running: python src/BE/main.py")
        print("2. Check your .env file has correct Azure credentials")
        print("3. Verify Azure services are accessible")
        sys.exit(1)


if __name__ == "__main__":
    main()
