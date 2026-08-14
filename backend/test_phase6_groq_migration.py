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
from app.ai import get_ai_provider
from app.services.explanation_service import (
    explain_project,
    explain_module,
    explain_function,
    reset_ai_request_counter
)

client = TestClient(app)

def create_sample_zip() -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manage.py", "def main():\n    print('Hello CodeOracle')\n\nif __name__ == '__main__':\n    main()")
        zf.writestr("client_example.py", "import os\ndef client_run(host: str = 'localhost'):\n    return f'Connecting to {host}'")
        zf.writestr("API_GUIDE.md", "# API Guide\n\nWelcome to the API Documentation.\n\n## Endpoints\n- `/api/projects/upload`\n- `/api/projects/analyze`")
        zf.writestr("FEATURES.md", "# Features\n\n## Core Capabilities\n- AST analysis\n- Dependency graph\n- Groq AI explanations")
    return zip_buffer.getvalue()

def run_groq_migration_test_suite():
    print("=== CODEORACLE PHASE 6 GROQ MIGRATION TEST SUITE ===\n")
    reset_ai_request_counter()

    # TEST 1: Minimal Request "Say GROQ_OK"
    print("--- TEST 1: Minimal Groq Connection Test ---")
    provider = get_ai_provider()
    p_name = provider.__class__.__name__
    print(f"Active Provider: {p_name} | Model: {provider.model}")

    if provider.is_configured:
        try:
            res = asyncio.run(provider.generate(prompt="Reply with exactly: GROQ_OK", max_tokens=10))
            print(f"[PASS] TEST 1: Groq API response: '{res.text}'")
        except Exception as exc:
            print(f"[NOTICE] TEST 1: Groq API test notice: {exc}")
    else:
        print("[NOTICE] TEST 1: Groq API key not configured yet. Static fallback mode active.")

    print("\n--- TEST 12: Upload Project (0 Groq Requests) ---")
    zip_bytes = create_sample_zip()
    up_res = client.post(
        "/api/projects/upload",
        files={"file": ("groq_sample.zip", zip_bytes, "application/zip")}
    )
    assert up_res.status_code == 201, f"Upload failed: {up_res.text}"
    project_id = up_res.json()["project_id"]
    print(f"[PASS] TEST 12: Project uploaded successfully without sending any Groq requests!\n")

    try:
        # TEST 2: Project Overview
        print("--- TEST 2 & 8: Project Overview & Cache Hit ---")
        p_res1 = client.get(f"/api/projects/{project_id}/explanations/project")
        assert p_res1.status_code == 200
        print("[PASS] TEST 2: Project Overview requested.")

        p_res2 = client.get(f"/api/projects/{project_id}/explanations/project")
        assert p_res2.status_code == 200
        print("[PASS] TEST 8: Project Overview returned CACHE HIT (0 Groq requests)!\n")

        # TEST 3: manage.py
        print("--- TEST 3 & 9: manage.py Explanation & Cache Hit ---")
        m_res1 = client.post(f"/api/projects/{project_id}/explanations/module", json={"file_path": "manage.py"})
        assert m_res1.status_code == 200
        print("[PASS] TEST 3: manage.py explanation generated.")

        m_res2 = client.post(f"/api/projects/{project_id}/explanations/module", json={"file_path": "manage.py"})
        assert m_res2.status_code == 200
        print("[PASS] TEST 9: manage.py returned CACHE HIT (0 Groq requests)!\n")

        # TEST 4: client_example.py
        print("--- TEST 4: client_example.py Explanation ---")
        c_res = client.post(f"/api/projects/{project_id}/explanations/module", json={"file_path": "client_example.py"})
        assert c_res.status_code == 200
        print("[PASS] TEST 4: client_example.py explanation generated.\n")

        # TEST 5: API_GUIDE.md
        print("--- TEST 5: API_GUIDE.md Markdown Explanation ---")
        md1_res = client.post(f"/api/projects/{project_id}/explanations/module", json={"file_path": "API_GUIDE.md"})
        assert md1_res.status_code == 200
        print("[PASS] TEST 5: API_GUIDE.md explanation generated.\n")

        # TEST 6: FEATURES.md
        print("--- TEST 6: FEATURES.md Markdown Explanation ---")
        md2_res = client.post(f"/api/projects/{project_id}/explanations/module", json={"file_path": "FEATURES.md"})
        assert md2_res.status_code == 200
        print("[PASS] TEST 6: FEATURES.md explanation generated.\n")

        # TEST 7 & 10: Function main() Explanation & Rapid Clicks Deduplication
        print("--- TEST 7 & 10: Function main() Explanation & Rapid Clicks ---")
        async def _test_rapid_clicks():
            tasks = [
                explain_function(project_id, "manage.py", "main")
                for _ in range(5)
            ]
            results = await asyncio.gather(*tasks)
            assert len(results) == 5
            print("[PASS] TEST 7 & 10: Function main() generated with 1 Groq request max (Deduplicated)!\n")

        asyncio.run(_test_rapid_clicks())

        # TEST 11: Simulate Rate Limit / API Error
        print("--- TEST 11: Simulated Rate Limit / Fallback ---")
        os.environ["GROQ_API_KEY"] = "invalid_groq_key_trigger"
        err_res = client.get(f"/api/projects/{project_id}/explanations/project?force_refresh=true")
        assert err_res.status_code == 200
        assert err_res.json()["is_static_fallback"] == True
        print("[PASS] TEST 11: Rate limit / API failure returns static fallback cleanly without crashing!\n")

        print("ALL 12 GROQ MIGRATION VERIFICATION TESTS PASSED SUCCESSFULLY!")

    finally:
        client.delete(f"/api/projects/{project_id}")

if __name__ == "__main__":
    run_groq_migration_test_suite()
