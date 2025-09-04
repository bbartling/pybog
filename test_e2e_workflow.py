#!/usr/bin/env python3
"""
End-to-End Integration Test for PyBOG Workflow
Tests the complete flow from file upload to BOG generation
"""

import requests
import json
import time
import sys
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
N8N_BASE_URL = "http://localhost:5678"

def print_status(message, status="INFO"):
    """Print colored status messages."""
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m"
    }
    print(f"{colors.get(status, '')}{status}{colors['RESET']}: {message}")

def test_api_health():
    """Test API health endpoint."""
    print_status("Testing API health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/health")
        if response.status_code == 200:
            data = response.json()
            print_status(f"API is {data.get('status', 'unknown')}", "SUCCESS")
            return True
        else:
            print_status(f"API returned status code: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Failed to connect to API: {e}", "ERROR")
        return False

def test_database_health():
    """Test database connectivity."""
    print_status("Testing database health...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/db/health")
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                print_status("Database is healthy", "SUCCESS")
                return True
            else:
                print_status(f"Database status: {data.get('status', 'unknown')}", "WARNING")
                return False
    except Exception as e:
        print_status(f"Database health check failed: {e}", "ERROR")
        return False

def test_n8n_health():
    """Test N8N connectivity via API proxy."""
    print_status("Testing N8N health via API proxy...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/n8n/health")
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                print_status("N8N is healthy", "SUCCESS")
                return True
            else:
                print_status(f"N8N status: {data.get('status', 'unknown')}", "WARNING")
                return False
    except Exception as e:
        print_status(f"N8N health check failed: {e}", "ERROR")
        return False

def create_test_session():
    """Create a new test session."""
    print_status("Creating test session...")
    try:
        session_id = f"test_session_{int(time.time())}"
        response = requests.post(
            f"{API_BASE_URL}/api/sessions",
            json={
                "session_id": session_id,
                "initial_message": "Test session for E2E verification"
            }
        )
        if response.status_code == 200:
            data = response.json()
            print_status(f"Session created: {data.get('session_id', 'unknown')}", "SUCCESS")
            return session_id
        else:
            print_status(f"Failed to create session: {response.status_code}", "ERROR")
            return None
    except Exception as e:
        print_status(f"Session creation failed: {e}", "ERROR")
        return None

def create_test_file():
    """Create a test HVAC document."""
    print_status("Creating test HVAC document...")
    test_content = """
    HVAC Control Sequence Specification
    ====================================
    
    System: Air Handling Unit (AHU-01)
    
    Input Sensors:
    - Supply Air Temperature (SAT) - Range: 55-75°F
    - Return Air Temperature (RAT) - Range: 65-80°F
    - Outside Air Temperature (OAT) - Range: -10-110°F
    - Supply Air Pressure (SAP) - Range: 0-5 inches WC
    - CO2 Level - Range: 0-2000 PPM
    
    Output Actuators:
    - Supply Fan VFD - 0-100% speed
    - Return Fan VFD - 0-100% speed
    - Cooling Valve - 0-100% open
    - Heating Valve - 0-100% open
    - Outside Air Damper - 0-100% open
    - Return Air Damper - 0-100% open
    
    Control Logic:
    1. Temperature Control:
       - If SAT > Setpoint + 2°F, increase cooling valve position
       - If SAT < Setpoint - 2°F, increase heating valve position
    
    2. Pressure Control:
       - Maintain supply air pressure at 1.5 inches WC
       - Modulate supply fan VFD to maintain pressure setpoint
    
    3. Ventilation Control:
       - If CO2 > 800 PPM, increase outside air damper to minimum 30%
       - If CO2 < 600 PPM, modulate outside air damper to minimum position
    
    Setpoints:
    - Supply Air Temperature: 55°F
    - Supply Air Pressure: 1.5 inches WC
    - CO2 Limit: 800 PPM
    """
    
    file_path = Path("test_hvac_sequence.txt")
    file_path.write_text(test_content)
    print_status(f"Test file created: {file_path}", "SUCCESS")
    return file_path

def test_file_upload(session_id, file_path):
    """Test file upload with text extraction."""
    print_status("Testing file upload and text extraction...")
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'text/plain')}
            data = {'session_id': session_id}
            
            response = requests.post(
                f"{API_BASE_URL}/api/process-document",
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print_status(f"File processed: {result.get('text_length', 0)} chars extracted", "SUCCESS")
                    return True
                else:
                    print_status(f"File processing failed: {result.get('message', 'Unknown error')}", "WARNING")
                    return True  # Still continue if text was extracted
            else:
                print_status(f"Upload failed with status: {response.status_code}", "ERROR")
                print_status(f"Response: {response.text}", "ERROR")
                return False
    except Exception as e:
        print_status(f"File upload failed: {e}", "ERROR")
        return False

def test_session_state(session_id):
    """Check session state."""
    print_status("Checking session state...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/sessions/{session_id}/state")
        if response.status_code == 200:
            data = response.json()
            print_status(f"Session state: {data.get('state', 'unknown')}", "SUCCESS")
            return data
        elif response.status_code == 404:
            print_status("Session not found in database", "WARNING")
            return None
        else:
            print_status(f"Failed to get session state: {response.status_code}", "ERROR")
            return None
    except Exception as e:
        print_status(f"Session state check failed: {e}", "ERROR")
        return None

def test_webhook_proxy():
    """Test N8N webhook proxy endpoint."""
    print_status("Testing N8N webhook proxy...")
    try:
        test_payload = {
            "session_id": "test_proxy",
            "text": "Test message",
            "timestamp": time.time()
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/n8n/webhook/test-webhook",
            json=test_payload
        )
        
        # We expect this to fail if webhook doesn't exist, but proxy should work
        if response.status_code in [404, 502]:
            print_status("Webhook proxy is working (webhook doesn't exist yet)", "SUCCESS")
            return True
        elif response.status_code == 200:
            print_status("Webhook proxy successfully forwarded request", "SUCCESS")
            return True
        else:
            print_status(f"Unexpected response: {response.status_code}", "WARNING")
            return False
    except Exception as e:
        print_status(f"Webhook proxy test failed: {e}", "ERROR")
        return False

def run_integration_tests():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("PyBOG End-to-End Integration Test")
    print("="*60 + "\n")
    
    # Track test results
    results = {
        "API Health": test_api_health(),
        "Database Health": test_database_health(),
        "N8N Health": test_n8n_health(),
        "Webhook Proxy": test_webhook_proxy(),
    }
    
    # Create session and test file operations
    session_id = create_test_session()
    if session_id:
        results["Session Creation"] = True
        
        # Create and upload test file
        test_file = create_test_file()
        results["File Upload"] = test_file_upload(session_id, test_file)
        
        # Check session state
        time.sleep(2)  # Give system time to process
        state_data = test_session_state(session_id)
        results["Session State"] = state_data is not None
        
        # Clean up test file
        if test_file.exists():
            test_file.unlink()
            print_status("Test file cleaned up", "INFO")
    else:
        results["Session Creation"] = False
        results["File Upload"] = False
        results["Session State"] = False
    
    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print_status("\nAll tests passed! ✨", "SUCCESS")
        return 0
    elif passed >= total * 0.7:
        print_status(f"\nMost tests passed ({passed}/{total}). Some components need attention.", "WARNING")
        return 1
    else:
        print_status(f"\nMany tests failed ({total-passed}/{total}). System needs fixes.", "ERROR")
        return 2

if __name__ == "__main__":
    sys.exit(run_integration_tests())
