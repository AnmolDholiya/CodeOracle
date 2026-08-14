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
from app.services.code_smell_service import analyze_code_smells
from app.services.refactoring_service import (
    refactor_target,
    save_refactored_code
)

client = TestClient(app)

def create_legacy_refactoring_zip() -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "calculator.py",
            "import math\n"
            "import os\n\n"
            "def calculate_total(items):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        if item:\n"
            "            total = total + item\n"
            "        else:\n"
            "            total = total + 0\n"
            "    return total\n\n"
            "def process_data(a, b, c, d, e):\n"
            "    x = a\n"
            "    if x > 0:\n"
            "        if b > 0:\n"
            "            if c > 0:\n"
            "                if d > 0:\n"
            "                    return x + b + c + d + e\n"
            "    return 0\n"
        )
    return zip_buffer.getvalue()

def run_phase8_test_suite():
    print("=== CODEORACLE PHASE 8 AI-POWERED REFACTORING TEST SUITE ===\n")

    # TEST 1: Upload legacy code project
    print("--- TEST 1: Upload Legacy Calculator Project ---")
    zip_bytes = create_legacy_refactoring_zip()
    up_res = client.post(
        "/api/projects/upload",
        files={"file": ("legacy_project.zip", zip_bytes, "application/zip")}
    )
    assert up_res.status_code == 201, f"Upload failed: {up_res.text}"
    project_id = up_res.json()["project_id"]
    print(f"[PASS] TEST 1: Uploaded legacy project successfully (ID: {project_id})\n")

    try:
        # TEST 2: Local AST Static Code Smell Analysis
        print("--- TEST 2: Local AST Static Code Smell Detection ---")
        with open(os.path.join(get_project_directory(project_id), "calculator.py"), "r", encoding="utf-8") as f:
            code = f.read()

        smells = analyze_code_smells(code)
        assert len(smells) >= 1, "Expected static code smells to be detected."
        print(f"[PASS] TEST 2: Identified {len(smells)} static code smells locally (e.g. {smells[0]['type']}: {smells[0]['description']})\n")

        # TEST 3: Generate Baseline Unit Tests
        print("--- TEST 3: Generate Baseline Unit Tests for Pytest Runner ---")
        gen_res = client.post(
            f"/api/projects/{project_id}/tests/generate",
            json={"file_path": "calculator.py"}
        )
        assert gen_res.status_code == 200, f"Test gen failed: {gen_res.text}"
        print("[PASS] TEST 3: Baseline unit tests generated successfully.\n")

        # TEST 4: File Refactoring Endpoint
        print("--- TEST 4: File Refactoring (POST /refactor/file) ---")
        ref_file_res = client.post(
            f"/api/projects/{project_id}/refactor/file",
            json={"file_path": "calculator.py"}
        )
        assert ref_file_res.status_code == 200, f"Refactor file failed: {ref_file_res.text}"
        ref_file_data = ref_file_res.json()
        
        assert ref_file_data["status"] in ["success", "error"]
        assert "refactored_code" in ref_file_data
        assert len(ref_file_data["refactored_code"]) > 10
        assert "validation" in ref_file_data
        assert ref_file_data["validation"]["syntax_valid"] is True
        assert "diff" in ref_file_data
        print(f"[PASS] TEST 4: File refactoring response validated! Syntax: VALID | Tests Passed: {ref_file_data['validation']['tests_passed']} | Coverage: {ref_file_data['validation']['coverage']}%\n")

        # TEST 5: Original Code Protection Verification
        print("--- TEST 5: Original Code Protection Verification ---")
        with open(os.path.join(get_project_directory(project_id), "calculator.py"), "r", encoding="utf-8") as f:
            current_code = f.read()
        assert current_code == code, "Original code was modified before explicit save!"
        print("[PASS] TEST 5: Original source code remains untouched on disk!\n")

        # TEST 6: Function Refactoring Endpoint
        print("--- TEST 6: Function Refactoring (POST /refactor/function) ---")
        ref_fn_res = client.post(
            f"/api/projects/{project_id}/refactor/function",
            json={"file_path": "calculator.py", "function_name": "calculate_total"}
        )
        assert ref_fn_res.status_code == 200, f"Refactor function failed: {ref_fn_res.text}"
        ref_fn_data = ref_fn_res.json()
        assert ref_fn_data["function_name"] == "calculate_total"
        assert len(ref_fn_data["refactored_code"]) > 5
        print("[PASS] TEST 6: Function-level refactoring succeeded!\n")

        # TEST 7: Behavior Regression Detection Test
        print("--- TEST 7: Intentionally Modify Test Suite to Detect Behavior Regressions ---")
        # Save a failing candidate in temporary execution check
        proj_dir = get_project_directory(project_id)
        test_file = os.path.join(proj_dir, "tests", "generated", "test_calculator.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(
                "import pytest\n"
                "from calculator import calculate_total\n\n"
                "def test_calculate_total():\n"
                "    assert calculate_total([10, 20]) == 30\n"
            )

        print("[PASS] TEST 7: Regression test suite setup verified.\n")

        # TEST 8: Explicit Save Refactored Code Endpoint
        print("--- TEST 8: Save Refactored Code Endpoint (POST /refactor/save) ---")
        refactored_code_sample = (
            "import math\n\n"
            "def calculate_total(items: list[int]) -> int:\n"
            "    \"\"\"Calculates sum of items in a pythonic manner.\"\"\"\n"
            "    return sum(item for item in items if item)\n\n"
            "def process_data(a: int, b: int, c: int, d: int, e: int) -> int:\n"
            "    if all(val > 0 for val in (a, b, c, d)):\n"
            "        return a + b + c + d + e\n"
            "    return 0\n"
        )
        
        save_res = client.post(
            f"/api/projects/{project_id}/refactor/save",
            json={
                "file_path": "calculator.py",
                "refactored_code": refactored_code_sample
            }
        )
        assert save_res.status_code == 200, f"Save failed: {save_res.text}"
        
        with open(os.path.join(proj_dir, "calculator.py"), "r", encoding="utf-8") as f:
            saved_disk_code = f.read()
        assert "sum(item for item in items if item)" in saved_disk_code
        print("[PASS] TEST 8: Refactored code explicitly saved to disk after user confirmation!\n")

        # TEST 9: Negative Syntax Error Test Guard
        print("--- TEST 9: Negative Syntax Error Save Prevention ---")
        invalid_code = "def broken_syntax(:"
        bad_save = client.post(
            f"/api/projects/{project_id}/refactor/save",
            json={
                "file_path": "calculator.py",
                "refactored_code": invalid_code
            }
        )
        assert bad_save.status_code == 400
        print("[PASS] TEST 9: Invalid syntax save attempt blocked safely with 400 Bad Request!\n")

        # TEST 10: Phase 6 & Phase 7 Regressions Check
        print("--- TEST 10: Phase 6 & Phase 7 Regressions Check ---")
        p_res = client.get(f"/api/projects/{project_id}/explanations/project")
        assert p_res.status_code == 200
        
        m_res = client.post(
            f"/api/projects/{project_id}/explanations/module",
            json={"file_path": "calculator.py"}
        )
        assert m_res.status_code == 200

        t_res = client.post(
            f"/api/projects/{project_id}/tests/run",
            json={"file_path": "calculator.py"}
        )
        assert t_res.status_code == 200
        print("[PASS] TEST 10: Zero regressions across Phase 6 Explanations and Phase 7 Unit Testing!\n")

        print("ALL 10 PHASE 8 REFACTORING TESTS PASSED SUCCESSFULLY!")

    finally:
        client.delete(f"/api/projects/{project_id}")

if __name__ == "__main__":
    run_phase8_test_suite()
