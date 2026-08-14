import sys
import os
import io
import zipfile
import asyncio
import time

# Ensure backend root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import load_backend_environment
load_backend_environment()

from fastapi.testclient import TestClient
from app.main import app
from app.services.extractor import get_project_directory
from app.services.unit_testing_service import (
    generate_unit_tests,
    run_unit_tests,
    get_test_coverage
)

client = TestClient(app)

def create_math_project_zip() -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "math_utils.py",
            "def add(a, b):\n"
            "    return a + b\n\n"
            "def divide(a, b):\n"
            "    if b == 0:\n"
            "        raise ValueError('Cannot divide by zero')\n"
            "    return a / b\n\n"
            "def is_even(n):\n"
            "    return n % 2 == 0\n"
        )
    return zip_buffer.getvalue()

def run_phase7_test_suite():
    print("=== CODEORACLE PHASE 7 UNIT TESTING & COVERAGE TEST SUITE ===\n")

    # TEST 1: Upload project containing math_utils.py
    print("--- TEST 1: Upload Math Utilities Project ---")
    zip_bytes = create_math_project_zip()
    up_res = client.post(
        "/api/projects/upload",
        files={"file": ("math_project.zip", zip_bytes, "application/zip")}
    )
    assert up_res.status_code == 201, f"Upload failed: {up_res.text}"
    project_id = up_res.json()["project_id"]
    print(f"[PASS] TEST 1: Uploaded math project successfully (ID: {project_id})\n")

    try:
        # TEST 2: Generate Unit Tests for math_utils.py
        print("--- TEST 2: AI Unit Test Generation & AST Syntax Check ---")
        gen_res = client.post(
            f"/api/projects/{project_id}/tests/generate",
            json={"file_path": "math_utils.py", "function_name": None}
        )
        assert gen_res.status_code == 200, f"Generation failed: {gen_res.text}"
        data = gen_res.json()
        assert "tests/generated/test_math_utils.py" in data["test_file_path"]
        assert len(data["test_code"]) > 10
        print(f"[PASS] TEST 2: Unit tests generated successfully at {data['test_file_path']}\n")

        # TEST 3: Execute Pytest Runner
        print("--- TEST 3: Pytest Automated Test Execution ---")
        exec_res = client.post(
            f"/api/projects/{project_id}/tests/run",
            json={"file_path": "math_utils.py", "timeout_seconds": 30}
        )
        assert exec_res.status_code == 200, f"Execution failed: {exec_res.text}"
        exec_data = exec_res.json()
        assert exec_data["status"] in ["passed", "failed", "completed"]
        print(f"[PASS] TEST 3: Pytest executed | Status: {exec_data['status']} | Passed: {exec_data['passed']}/{exec_data['total']} in {exec_data['duration_seconds']}s\n")

        # TEST 4: Calculate Actual Coverage via coverage.py
        print("--- TEST 4: Actual Code Coverage Measurement (coverage.py) ---")
        cov_res = client.get(f"/api/projects/{project_id}/tests/coverage?file_path=math_utils.py")
        assert cov_res.status_code == 200, f"Coverage failed: {cov_res.text}"
        cov_data = cov_res.json()
        print(f"[PASS] TEST 4: Actual coverage calculated: {cov_data['overall_coverage']}% | Statements: {cov_data['total_statements']} | Missed: {cov_data['total_missed']}\n")

        # TEST 5: Intentionally Test Failing Assertion Handling
        print("--- TEST 5: Intentionally Test Failing Test Case ---")
        proj_dir = get_project_directory(project_id)
        test_file_abs = os.path.join(proj_dir, "tests", "generated", "test_failing.py")
        os.makedirs(os.path.dirname(test_file_abs), exist_ok=True)
        with open(test_file_abs, "w", encoding="utf-8") as f:
            f.write("import pytest\ndef test_intentional_failure():\n    assert 1 == 2\n")

        fail_exec = run_unit_tests(project_id, "math_utils.py", timeout_seconds=15)
        assert fail_exec.failed >= 1 or fail_exec.status == "failed"
        print(f"[PASS] TEST 5: Failure correctly detected | Status: {fail_exec.status} | Failed count: {fail_exec.failed}\n")

        # TEST 6: Intentionally Test Timeout Handling
        print("--- TEST 6: Intentionally Test Execution Timeout Guard ---")
        timeout_file_abs = os.path.join(proj_dir, "tests", "generated", "test_timeout.py")
        with open(timeout_file_abs, "w", encoding="utf-8") as f:
            f.write("import time\ndef test_sleeping():\n    time.sleep(5)\n")

        timeout_exec = run_unit_tests(project_id, "math_utils.py", timeout_seconds=1)
        assert timeout_exec.status == "timeout"
        print("[PASS] TEST 6: Timeout limit intercepted safely | Status: timeout\n")

        # TEST 7: Security Path Traversal Guard
        print("--- TEST 7: Security Path Traversal Prevention ---")
        bad_res = client.post(
            f"/api/projects/{project_id}/tests/generate",
            json={"file_path": "../../etc/passwd.py"}
        )
        assert bad_res.status_code in [400, 404]
        print("[PASS] TEST 7: Security path traversal outside workspace prevented!\n")

        # TEST 8: Phase 6 Regression Check
        print("--- TEST 8: Phase 6 Regression Test ---")
        p_res = client.get(f"/api/projects/{project_id}/explanations/project")
        assert p_res.status_code == 200
        print("[PASS] TEST 8: Phase 6 Project Overview still functioning perfectly with Groq!\n")

        print("ALL 8 PHASE 7 UNIT TESTING & COVERAGE TESTS PASSED SUCCESSFULLY!")

    finally:
        client.delete(f"/api/projects/{project_id}")

if __name__ == "__main__":
    run_phase7_test_suite()
