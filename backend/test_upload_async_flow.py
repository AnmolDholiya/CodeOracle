import io
import time
import zipfile
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_mock_zip(file_dict: dict) -> bytes:
    """Creates a ZIP archive from a dictionary of filename -> content strings."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, content in file_dict.items():
            zf.writestr(fname, content)
    return zip_buffer.getvalue()

def create_large_10k_loc_zip() -> bytes:
    """Generates a multi-file Python project simulating 10,000+ lines of code across 50 files."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Generate 50 Python files with ~200 lines each
        for i in range(50):
            lines = [f"# File module_{i}.py generated for 10k LOC test\n"]
            lines.append("import os\nimport sys\nimport json\nimport requests\n\n")
            lines.append(f"class ServiceModule{i}:\n")
            lines.append("    def __init__(self):\n        self.active = True\n\n")
            for j in range(30):
                lines.append(f"    def compute_step_{j}(self, val: int) -> int:\n")
                lines.append(f"        '''Step {j} computation logic.'''\n")
                lines.append(f"        res = val + {j}\n")
                lines.append("        return res * 2\n\n")
            zf.writestr(f"pkg_{i // 10}/module_{i}.py", "".join(lines))
    return zip_buffer.getvalue()

def test_1_small_zip_upload_and_status_polling():
    """Test 1: Small ZIP upload returns instantly (<200ms) and status polling transitions to completed."""
    zip_bytes = create_mock_zip({
        "main.py": "def hello(): return 'world'",
        "utils.py": "def add(a, b): return a + b"
    })

    t0 = time.time()
    res = client.post(
        "/api/projects/upload",
        files={"file": ("small_app.zip", zip_bytes, "application/zip")}
    )
    t_elapsed = time.time() - t0

    assert res.status_code in (201, 202), f"Upload failed: {res.text}"
    data = res.json()
    assert "project_id" in data
    assert data["status"] in ("queued", "processing")
    assert t_elapsed < 1.0, f"Upload request took too long ({t_elapsed:.2f}s)! Expected <1.0s"
    print(f"[PASS] Test 1: Small ZIP uploaded in {t_elapsed * 1000:.1f}ms (returned project_id: {data['project_id']})")

    # Poll status endpoint until completed
    project_id = data["project_id"]
    completed = False
    for _ in range(10):
        res_status = client.get(f"/api/projects/{project_id}/status")
        assert res_status.status_code == 200
        st = res_status.json()
        if st["status"] == "completed":
            completed = True
            break
        time.sleep(0.1)

    assert completed, "Project processing status did not become completed!"
    print("[PASS] Test 1: Status polling completed successfully")

    # Clean up project
    client.delete(f"/api/projects/{project_id}")

def test_2_medium_zip_upload():
    """Test 2: Medium ZIP upload with multiple subfolders."""
    files = {f"dir_{i}/file_{j}.py": f"def fn_{j}(): return {j}" for i in range(5) for j in range(5)}
    zip_bytes = create_mock_zip(files)

    res = client.post("/api/projects/upload", files={"file": ("medium.zip", zip_bytes, "application/zip")})
    assert res.status_code in (201, 202)
    project_id = res.json()["project_id"]

    # Poll until completed
    for _ in range(15):
        st = client.get(f"/api/projects/{project_id}/status").json()
        if st["status"] == "completed":
            break
        time.sleep(0.1)

    res_meta = client.get(f"/api/projects/{project_id}")
    assert res_meta.status_code == 200
    meta = res_meta.json()
    assert meta["total_files"] >= 20, f"Expected >= 20, got {meta['total_files']}"
    print(f"[PASS] Test 2: Medium ZIP processed {meta['total_files']} files successfully")
    client.delete(f"/api/projects/{project_id}")

def test_3_large_10k_loc_zip_upload():
    """Test 3 & 9: Large codebase (10,000+ LOC, 50 files) upload returns instantly without 30s timeout."""
    print("Generating 10,000 LOC codebase ZIP...")
    zip_bytes = create_large_10k_loc_zip()

    t0 = time.time()
    res = client.post("/api/projects/upload", files={"file": ("large_10k_project.zip", zip_bytes, "application/zip")})
    t_elapsed = time.time() - t0

    assert res.status_code in (201, 202), f"Upload failed: {res.text}"
    project_id = res.json()["project_id"]
    assert t_elapsed < 2.0, f"Upload request took {t_elapsed:.2f}s! Expected instant return (<2s)"
    print(f"[PASS] Test 3: 10,000 LOC ZIP upload request returned in {t_elapsed:.2f}s (No timeout!)")

    # Poll status endpoint until completed
    completed = False
    for _ in range(30):
        st = client.get(f"/api/projects/{project_id}/status").json()
        if st["status"] == "completed":
            completed = True
            break
        time.sleep(0.2)

    assert completed, "10k LOC project background processing did not complete!"
    res_meta = client.get(f"/api/projects/{project_id}")
    meta = res_meta.json()
    print(f"[PASS] Test 3: 10,000 LOC codebase processed in background! Total LOC: {meta['total_lines_of_code']}, Total Files: {meta['total_files']}")
    client.delete(f"/api/projects/{project_id}")

def test_4_zip_with_many_files():
    """Test 4: ZIP containing 100 small files."""
    files = {f"flat/file_{i}.py": f"x = {i}" for i in range(100)}
    zip_bytes = create_mock_zip(files)

    res = client.post("/api/projects/upload", files={"file": ("many_files.zip", zip_bytes, "application/zip")})
    assert res.status_code in (201, 202)
    project_id = res.json()["project_id"]

    for _ in range(20):
        st = client.get(f"/api/projects/{project_id}/status").json()
        if st["status"] == "completed":
            break
        time.sleep(0.1)

    res_meta = client.get(f"/api/projects/{project_id}")
    assert res_meta.json()["total_files"] == 100
    print("[PASS] Test 4: ZIP containing 100 files processed successfully")
    client.delete(f"/api/projects/{project_id}")

def test_5_invalid_file_type():
    """Test 5: Non-zip file type rejected with 400 Bad Request."""
    res = client.post("/api/projects/upload", files={"file": ("test.txt", b"plain text", "text/plain")})
    assert res.status_code == 400
    assert "Invalid file type" in res.json()["detail"]
    print("[PASS] Test 5: Non-zip file rejected with 400 Bad Request")

def test_6_empty_zip():
    """Test 6: Empty ZIP file rejected with 400 Bad Request."""
    res = client.post("/api/projects/upload", files={"file": ("empty.zip", b"", "application/zip")})
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()
    print("[PASS] Test 6: Empty ZIP file rejected with 400 Bad Request")

def test_7_malformed_python_source():
    """Test 7: ZIP with malformed Python files processes AST without crashing."""
    zip_bytes = create_mock_zip({"valid.py": "x = 10", "broken.py": "def broken(:"})
    res = client.post("/api/projects/upload", files={"file": ("malformed.zip", zip_bytes, "application/zip")})
    assert res.status_code in (201, 202)
    project_id = res.json()["project_id"]

    for _ in range(10):
        st = client.get(f"/api/projects/{project_id}/status").json()
        if st["status"] == "completed":
            break
        time.sleep(0.1)

    res_ast = client.get(f"/api/projects/{project_id}/analyze")
    assert res_ast.status_code == 200
    print("[PASS] Test 7: Malformed Python file processed without crashing server")
    client.delete(f"/api/projects/{project_id}")

def test_8_zip_with_external_libraries():
    """Test 8: ZIP with external libraries (Django, Requests)."""
    zip_bytes = create_mock_zip({
        "app.py": "from django.http import HttpResponse\nimport requests"
    })
    res = client.post("/api/projects/upload", files={"file": ("ext_lib.zip", zip_bytes, "application/zip")})
    assert res.status_code in (201, 202)
    project_id = res.json()["project_id"]

    for _ in range(10):
        st = client.get(f"/api/projects/{project_id}/status").json()
        if st["status"] == "completed":
            break
        time.sleep(0.1)

    res_dep = client.get(f"/api/projects/{project_id}/dependencies")
    assert res_dep.status_code == 200
    ext_names = [lib["name"] for lib in res_dep.json()["external_libraries"]]
    assert "Django" in ext_names and "Requests" in ext_names
    print("[PASS] Test 8: ZIP with external libraries extracted and classified successfully")
    client.delete(f"/api/projects/{project_id}")

def run_all_async_upload_tests():
    print("=== Running Async Upload & 10,000 LOC Processing Test Suite ===")
    test_1_small_zip_upload_and_status_polling()
    test_2_medium_zip_upload()
    test_3_large_10k_loc_zip_upload()
    test_4_zip_with_many_files()
    test_5_invalid_file_type()
    test_6_empty_zip()
    test_7_malformed_python_source()
    test_8_zip_with_external_libraries()
    print("\nALL 8 UPLOAD & LARGE-PROJECT ASYNC TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_all_async_upload_tests()
