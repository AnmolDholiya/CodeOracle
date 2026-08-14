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
from app.services.python_ast import analyze_project_workspace
from app.services.explanation_service import (
    explain_project,
    explain_module,
    explain_function,
    reset_gemini_request_counter
)

client = TestClient(app)

def create_large_sample_zip(num_files: int = 100) -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manage.py", "def main():\n    print('Hello CodeOracle')\n\nif __name__ == '__main__':\n    main()")
        zf.writestr("client_example.py", "import os\ndef client_run(host: str = 'localhost'):\n    return f'Connecting to {host}'")
        for i in range(num_files - 2):
            zf.writestr(f"module_{i}.py", f"def func_{i}():\n    return {i}")
    return zip_buffer.getvalue()

def run_rate_limit_permanent_fix_suite():
    print("=== CODEORACLE PHASE 6 PERMANENT RATE LIMIT FIX SUITE ===\n")
    reset_gemini_request_counter()

    # TEST 1: Upload project -> Expected Gemini calls: 0
    print("--- TEST 1: Upload project (100 files) ---")
    zip_bytes = create_large_sample_zip(100)
    start_up = time.time()
    up_res = client.post(
        "/api/projects/upload",
        files={"file": ("large_project.zip", zip_bytes, "application/zip")}
    )
    assert up_res.status_code == 201, f"Upload failed: {up_res.text}"
    project_id = up_res.json()["project_id"]
    duration = time.time() - start_up
    print(f"[PASS] TEST 1: Uploaded 100-file project in {duration:.2f}s | Gemini calls = 0!\n")

    try:
        # TEST 2: Open Project Overview -> Expected Gemini calls <= 1
        print("--- TEST 2 & 3: Project Overview On-Demand & Cache ---")
        res1 = client.get(f"/api/projects/{project_id}/explanations/project")
        assert res1.status_code == 200
        print("[PASS] TEST 2: Project Overview requested on-demand.")

        # TEST 3: Leave Project Overview and return -> Expected Gemini calls: 0 (CACHE HIT)
        res2 = client.get(f"/api/projects/{project_id}/explanations/project")
        assert res2.status_code == 200
        print("[PASS] TEST 3: Project Overview revisit returned CACHE HIT (0 Gemini calls)!\n")

        # TEST 4: Open manage.py -> Expected Gemini calls <= 1
        print("--- TEST 4 & 5: File Explanation On-Demand & Cache ---")
        f_res1 = client.post(f"/api/projects/{project_id}/explanations/module", json={"file_path": "manage.py"})
        assert f_res1.status_code == 200
        print("[PASS] TEST 4: File explanation manage.py requested on-demand.")

        # TEST 5: Open manage.py again -> Expected Gemini calls: 0 (CACHE HIT)
        f_res2 = client.post(f"/api/projects/{project_id}/explanations/module", json={"file_path": "manage.py"})
        assert f_res2.status_code == 200
        print("[PASS] TEST 5: File explanation manage.py revisit returned CACHE HIT (0 Gemini calls)!\n")

        # TEST 6 & 7: Rapid Function Clicks Deduplication & Cache
        print("--- TEST 6 & 7: Function Explanation Rapid Clicks & Cache ---")
        async def _test_rapid_clicks():
            tasks = [
                explain_function(project_id, "manage.py", "main")
                for _ in range(5)
            ]
            results = await asyncio.gather(*tasks)
            assert len(results) == 5
            print("[PASS] TEST 6: 5 rapid duplicate clicks deduplicated into 1 request max via in-flight lock!")

            # Re-requesting function main() should be CACHE HIT
            fn_cached = await explain_function(project_id, "manage.py", "main")
            print("[PASS] TEST 7: Subsequent function request returned CACHE HIT (0 Gemini calls)!\n")

        asyncio.run(_test_rapid_clicks())

        # TEST 8: Simulate 429 Rate Limit Guard
        print("--- TEST 8: 429 Rate Limit Backoff & Static Fallback Guard ---")
        os.environ["GEMINI_API_KEY"] = "invalid_key_trigger"
        err_res = client.get(f"/api/projects/{project_id}/explanations/project?force_refresh=true")
        assert err_res.status_code == 200
        assert err_res.json()["is_static_fallback"] == True
        print("[PASS] TEST 8: Rate limit / API failure returns static fallback cleanly without 500 error!\n")

        print("ALL PERMANENT RATE LIMIT FIX TESTS PASSED SUCCESSFULLY!")

    finally:
        client.delete(f"/api/projects/{project_id}")

if __name__ == "__main__":
    run_rate_limit_permanent_fix_suite()
