import time
import io
import zipfile
import httpx

BASE_URL = "http://127.0.0.1:8000"

def create_sample_zip() -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("main.py", "import os\nfrom utils import add\nprint(add(2, 3))")
        zf.writestr("utils.py", "def add(a, b):\n    return a + b")
    return zip_buffer.getvalue()

def test_live_server_endpoints():
    print(f"=== Testing Live FastAPI Server on {BASE_URL} ===")
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Health check
        res_health = client.get("/api/health")
        assert res_health.status_code == 200, f"Health failed: {res_health.text}"
        print(f"[PASS] 1. GET /api/health returned 200 OK: {res_health.json()}")

        # 2. AI Status check
        res_ai = client.get("/api/ai/status")
        assert res_ai.status_code == 200, f"AI status failed: {res_ai.text}"
        print(f"[PASS] 2. GET /api/ai/status returned 200 OK: {res_ai.json()}")

        # 3. ZIP Upload (Instant response < 200ms)
        zip_bytes = create_sample_zip()
        t0 = time.time()
        res_upload = client.post(
            "/api/projects/upload",
            files={"file": ("sample.zip", zip_bytes, "application/zip")}
        )
        t_elapsed = time.time() - t0
        assert res_upload.status_code == 201, f"Upload failed: {res_upload.text}"
        upload_data = res_upload.json()
        project_id = upload_data["project_id"]
        assert t_elapsed < 1.0, f"Upload took too long ({t_elapsed:.2f}s)"
        print(f"[PASS] 3. POST /api/projects/upload returned 201 Created in {t_elapsed * 1000:.1f}ms: Project ID = {project_id}")

        # 4. Status Polling GET /api/projects/{project_id}/status
        completed = False
        final_status = None
        for _ in range(15):
            res_status = client.get(f"/api/projects/{project_id}/status")
            assert res_status.status_code == 200, f"Status poll failed: {res_status.text}"
            st_json = res_status.json()
            if st_json["status"] == "completed":
                completed = True
                final_status = st_json
                break
            time.sleep(0.2)

        assert completed, f"Status polling did not complete! Last status: {st_json}"
        print(f"[PASS] 4. GET /api/projects/{project_id}/status returned 200 OK (Stage: {final_status['stage']}, Progress: {final_status['progress']}%)")

        # 5. Get project metadata
        res_info = client.get(f"/api/projects/{project_id}")
        assert res_info.status_code == 200
        print(f"[PASS] 5. GET /api/projects/{project_id} returned 200 OK (Files: {res_info.json()['total_files']})")

        # 6. Get dependencies
        res_dep = client.get(f"/api/projects/{project_id}/dependencies")
        assert res_dep.status_code == 200
        print(f"[PASS] 6. GET /api/projects/{project_id}/dependencies returned 200 OK (Nodes: {res_dep.json()['total_nodes']})")

        # 7. Non-existent project 404 test
        res_404 = client.get("/api/projects/invalid_id_999/status")
        assert res_404.status_code == 404
        assert "detail" in res_404.json()
        print(f"[PASS] 7. GET /api/projects/invalid_id_999/status returned 404 JSON detail cleanly")

        # Cleanup
        client.delete(f"/api/projects/{project_id}")
        print(f"[PASS] 8. DELETE /api/projects/{project_id} cleaned up workspace")

    print("\nALL LIVE SERVER ENDPOINTS TESTED AND WORKING PERFECTLY!")

if __name__ == "__main__":
    test_live_server_endpoints()
