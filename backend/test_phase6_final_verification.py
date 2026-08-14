import sys
import os
import io
import zipfile
import json

# Ensure backend root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import load_backend_environment
load_backend_environment()

from fastapi.testclient import TestClient
from app.main import app
from app.ai.schemas import ProjectExplanation, ModuleExplanation, FunctionExplanation

client = TestClient(app)

def create_sample_zip() -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manage.py", "def main():\n    print('Hello CodeOracle')\n\nif __name__ == '__main__':\n    main()")
        zf.writestr("client_example.py", "import os\ndef client_run(host: str = 'localhost'):\n    return f'Connecting to {host}'")
        zf.writestr("API_GUIDE.md", "# API Guide\nDetailed guide for legacy codebase modernizer.")
        zf.writestr("FEATURES.md", "# Features\n1. AST Analysis\n2. AI Code Explainer")
        zf.writestr(".gitignore", "*.pyc\n__pycache__/\n.env")
    return zip_buffer.getvalue()

def run_phase6_final_verification():
    print("=== CODEORACLE PHASE 6 FINAL VERIFICATION SUITE ===")
    zip_bytes = create_sample_zip()
    up_res = client.post(
        "/api/projects/upload",
        files={"file": ("legacy_project.zip", zip_bytes, "application/zip")}
    )
    assert up_res.status_code in (201, 202), f"Upload failed: {up_res.text}"
    project_id = up_res.json()["project_id"]
    print(f"[Uploaded Project ID]: {project_id}\n")

    try:
        # TEST 1: Project Overview
        proj_res = client.get(f"/api/projects/{project_id}/explanations/project")
        assert proj_res.status_code == 200, f"TEST 1 Failed HTTP {proj_res.status_code}"
        proj_data = proj_res.json()
        validated_proj = ProjectExplanation.model_validate(proj_data)
        print("[PASS] TEST 1: Project Overview (Valid Schema, Fallback state:", validated_proj.is_static_fallback, ")")

        # TEST 2: Python file explanation (manage.py)
        py1_res = client.post(f"/api/projects/{project_id}/explanations/module", json={"file_path": "manage.py"})
        assert py1_res.status_code == 200, f"TEST 2 Failed HTTP {py1_res.status_code}"
        py1_data = py1_res.json()
        validated_py1 = ModuleExplanation.model_validate(py1_data)
        print("[PASS] TEST 2: File Explanation (manage.py) (Valid Schema, Fallback state:", validated_py1.is_static_fallback, ")")

        # TEST 3: Python file explanation (client_example.py)
        py2_res = client.post(f"/api/projects/{project_id}/explanations/module", json={"file_path": "client_example.py"})
        assert py2_res.status_code == 200, f"TEST 3 Failed HTTP {py2_res.status_code}"
        py2_data = py2_res.json()
        validated_py2 = ModuleExplanation.model_validate(py2_data)
        print("[PASS] TEST 3: File Explanation (client_example.py) (Valid Schema, Fallback state:", validated_py2.is_static_fallback, ")")

        # TEST 4: Markdown file explanation (API_GUIDE.md)
        md_res = client.post(f"/api/projects/{project_id}/explanations/module", json={"file_path": "API_GUIDE.md"})
        assert md_res.status_code == 200, f"TEST 4 Failed HTTP {md_res.status_code}"
        md_data = md_res.json()
        validated_md = ModuleExplanation.model_validate(md_data)
        print("[PASS] TEST 4: File Explanation (API_GUIDE.md) (Valid Schema, Fallback state:", validated_md.is_static_fallback, ")")

        # TEST 5: Function explanation (main())
        fn_res = client.post(f"/api/projects/{project_id}/explanations/function", json={"file_path": "manage.py", "function_name": "main"})
        assert fn_res.status_code == 200, f"TEST 5 Failed HTTP {fn_res.status_code}"
        fn_data = fn_res.json()
        validated_fn = FunctionExplanation.model_validate(fn_data)
        print("[PASS] TEST 5: Function Explanation (main()) (Valid Schema, Fallback state:", validated_fn.is_static_fallback, ")")

        # TEST 6: Force Gemini failure / unconfigured state -> static fallback
        print("\n--- TEST 6: Verifying Static Fallback UI Guard ---")
        os.environ["GEMINI_API_KEY"] = "invalid_key_for_testing"
        from app.ai import get_ai_provider
        fallback_proj_res = client.get(f"/api/projects/{project_id}/explanations/project?force_refresh=true")
        assert fallback_proj_res.status_code == 200
        fallback_data = fallback_proj_res.json()
        assert fallback_data.get("is_static_fallback") == True, "Fallback flag should be True"
        print("[PASS] TEST 6: Static Analysis Fallback triggered gracefully without 500 error!")

        print("\nALL 6 VERIFICATION TESTS PASSED SUCCESSFULLY!")

    finally:
        client.delete(f"/api/projects/{project_id}")

if __name__ == "__main__":
    run_phase6_final_verification()
