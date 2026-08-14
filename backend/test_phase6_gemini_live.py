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

client = TestClient(app)

def create_sample_zip() -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manage.py", "def main(): print('Hello CodeOracle')")
        zf.writestr("client_example.py", "import os\ndef client_run(): return True")
        zf.writestr("API_GUIDE.md", "# API Guide\nDetailed guide for legacy codebase modernizer.")
    return zip_buffer.getvalue()

def test_gemini_live_explanations():
    zip_bytes = create_sample_zip()
    up_res = client.post(
        "/api/projects/upload",
        files={"file": ("legacy_project.zip", zip_bytes, "application/zip")}
    )
    assert up_res.status_code == 201, f"Upload failed: {up_res.text}"
    project_id = up_res.json()["project_id"]
    print(f"\n[Project Created]: {project_id}")

    try:
        # 1. Test Project Overview Explanation
        proj_res = client.get(f"/api/projects/{project_id}/explanations/project")
        assert proj_res.status_code == 200, f"Project explanation HTTP error: {proj_res.text}"
        proj_data = proj_res.json()
        print("\n--- Project Overview Gemini Live Result ---")
        print("Purpose:", proj_data.get("purpose"))
        print("Architecture:", proj_data.get("architecture"))
        print("Is Static Fallback:", proj_data.get("is_static_fallback"))

        # 2. Test File Explanation for Python file (manage.py)
        py_res = client.post(
            f"/api/projects/{project_id}/explanations/module",
            json={"file_path": "manage.py"}
        )
        assert py_res.status_code == 200, f"Python file explanation HTTP error: {py_res.text}"
        py_data = py_res.json()
        print("\n--- File Explanation (manage.py) Gemini Live Result ---")
        print("Purpose:", py_data.get("purpose"))
        print("Summary:", py_data.get("summary"))
        print("Responsibilities:", py_data.get("responsibilities"))
        print("Is Static Fallback:", py_data.get("is_static_fallback"))

        # 3. Test Non-Python File Explanation (API_GUIDE.md)
        md_res = client.post(
            f"/api/projects/{project_id}/explanations/module",
            json={"file_path": "API_GUIDE.md"}
        )
        assert md_res.status_code == 200, f"Markdown file explanation HTTP error: {md_res.text}"
        md_data = md_res.json()
        print("\n--- File Explanation (API_GUIDE.md) Gemini Live Result ---")
        print("Purpose:", md_data.get("purpose"))
        print("Summary:", md_data.get("summary"))
        print("Is Static Fallback:", md_data.get("is_static_fallback"))

        print("\nALL GEMINI LIVE EXPLANATION TESTS PASSED SUCCESSFULLY!")

    finally:
        client.delete(f"/api/projects/{project_id}")

if __name__ == "__main__":
    test_gemini_live_explanations()
