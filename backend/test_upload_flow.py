import os
import time
import zipfile
import io
from fastapi.testclient import TestClient
from app.main import app
from app.services.extractor import is_safe_path

client = TestClient(app)

def test_phase2_flow():
    print("=== Testing Phase 2 ZIP Upload & Temporary Workspace Management ===")

    # 1. Reject non-zip file
    res = client.post("/api/projects/upload", files={"file": ("test.txt", b"hello world", "text/plain")})
    assert res.status_code == 400, f"Expected 400 for non-zip, got {res.status_code}"
    print("[PASS] 1. Reject non-zip file test passed")

    # 2. Reject empty zip file
    res = client.post("/api/projects/upload", files={"file": ("empty.zip", b"", "application/zip")})
    assert res.status_code == 400, f"Expected 400 for empty zip, got {res.status_code}"
    print("[PASS] 2. Reject empty zip file test passed")

    # 3. Test path traversal safety helper
    assert is_safe_path("/tmp/base", "/tmp/base/file.txt") == True
    assert is_safe_path("/tmp/base", "/tmp/base/sub/file.txt") == True
    assert is_safe_path("/tmp/base", "/tmp/base/../other/file.txt") == False
    print("[PASS] 3. Path traversal security checks passed")

    # 4. Upload valid sample Python ZIP (sample_legacy.zip)
    sample_zip_path = "sample_legacy.zip" if os.path.exists("sample_legacy.zip") else os.path.join("..", "sample_legacy.zip")
    with open(sample_zip_path, "rb") as f:
        sample_zip_bytes = f.read()

    res = client.post("/api/projects/upload", files={"file": ("sample_legacy.zip", sample_zip_bytes, "application/zip")})
    assert res.status_code in (201, 202), f"Expected 201/202, got {res.status_code}: {res.text}"
    data = res.json()
    
    project_id = data["project_id"]
    print(f"[PASS] 4. Uploaded ZIP successfully. Project ID: {project_id}")

    # Poll status until processing completes
    for _ in range(20):
        time.sleep(0.2)
        st_res = client.get(f"/api/projects/{project_id}/status")
        if st_res.status_code == 200 and st_res.json().get("status") == "completed":
            break

    # 5. Retrieve project metadata GET /api/projects/{project_id}
    res_info = client.get(f"/api/projects/{project_id}")
    assert res_info.status_code == 200, f"Expected 200, got {res_info.status_code}"
    info_data = res_info.json()
    assert info_data["project_id"] == project_id
    assert info_data["total_files"] == 2
    assert "Python" in info_data["languages"]
    assert any(f["relative_path"] == "main.py" for f in info_data["files"])
    print(f"[PASS] 5. GET /api/projects/{project_id} returned expected project metadata")

    # 6. Cleanup temporary project DELETE /api/projects/{project_id}
    res_del = client.delete(f"/api/projects/{project_id}")
    assert res_del.status_code == 200
    print(f"[PASS] 6. DELETE /api/projects/{project_id} cleaned up temp workspace successfully")

    # 7. Verify project directory no longer exists
    res_info_after = client.get(f"/api/projects/{project_id}")
    assert res_info_after.status_code == 404
    print("[PASS] 7. Verified temp workspace was completely purged (404 on subsequent requests)")

    print("\nALL PHASE 2 BACKEND ENDPOINT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_phase2_flow()
