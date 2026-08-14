import io
import os
import time
import zipfile
import string
import random
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_synthetic_zip(target_mb: float, file_count: int = 20) -> bytes:
    """Generates a real valid ZIP archive of exact specified compressed size containing python code."""
    buf = io.BytesIO()
    # Estimate raw bytes needed to produce target compressed size (with random uncompressible bytes)
    bytes_per_file = int((target_mb * 1024 * 1024) / max(file_count, 1))
    
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for i in range(file_count):
            code_lines = [
                f"# Module {i} for load testing",
                "import os",
                "import sys",
                f"def calculate_metric_{i}(x, y):",
                f"    '''Calculates metric {i}'''",
                f"    return (x * {i} + y) / {max(i, 1)}",
                "",
                f"class ServiceHandler_{i}:",
                f"    def __init__(self, name='service_{i}'):",
                f"        self.name = name",
                "    def process(self, data):",
                "        return [x for x in data if x is not None]",
                ""
            ]
            code = "\n".join(code_lines)
            
            # Pad with pseudo-random alphanumeric comment to prevent excessive compression
            pad_needed = max(0, bytes_per_file - len(code.encode("utf-8")))
            if pad_needed > 0:
                random_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=min(pad_needed, 50000)))
                # Repeat the random chunk to fill pad_needed
                multiplier = (pad_needed // len(random_chars)) + 1
                full_pad = (random_chars * multiplier)[:pad_needed]
                code += f"\n# DUMMY DATA:\n# {full_pad}\n"
                
            z.writestr(f"pkg_{i // 5}/module_{i}.py", code)
            
    return buf.getvalue()

import pytest

@pytest.mark.parametrize("label,target_mb", [
    ("1 MB ZIP", 1.0),
    ("10 MB ZIP", 10.0),
    ("50 MB ZIP", 50.0),
    ("135 MB ZIP (Production Target)", 135.0),
])
def test_zip_upload_size(label: str, target_mb: float):
    print(f"\n==================================================")
    print(f"TESTING {label} ({target_mb:.1f} MB)")
    print(f"==================================================")
    
    t_gen_0 = time.time()
    zip_bytes = create_synthetic_zip(target_mb, file_count=min(100, max(10, int(target_mb * 2))))
    actual_mb = len(zip_bytes) / (1024 * 1024)
    print(f"[GENERATE] Created {actual_mb:.2f} MB synthetic ZIP in {time.time() - t_gen_0:.2f}s")
    
    # 1. Stream Upload
    t_up_0 = time.time()
    res = client.post(
        "/api/projects/upload",
        files={"file": (f"test_{label.lower().replace(' ', '_')}.zip", zip_bytes, "application/zip")}
    )
    t_upload = time.time() - t_up_0
    
    assert res.status_code == 202, f"Upload failed with {res.status_code}: {res.text}"
    data = res.json()
    project_id = data["project_id"]
    print(f"[UPLOAD] HTTP 202 Accepted in {t_upload:.3f}s. project_id={project_id}")
    
    # 2. Poll Status
    t_poll_0 = time.time()
    max_wait_seconds = 120
    completed = False
    last_stage = ""
    
    while time.time() - t_poll_0 < max_wait_seconds:
        st_res = client.get(f"/api/projects/{project_id}/status")
        assert st_res.status_code == 200
        st = st_res.json()
        
        if st["stage"] != last_stage:
            last_stage = st["stage"]
            print(f"  -> Stage: {st['stage']} ({st['progress']}%) - {st['message']}")
            
        if st["status"] == "completed":
            completed = True
            break
        elif st["status"] == "failed":
            raise RuntimeError(f"Processing failed: {st.get('error') or st.get('message')}")
            
        time.sleep(0.3)
        
    t_processing = time.time() - t_poll_0
    assert completed, f"Processing did not complete within {max_wait_seconds}s! Last status: {st}"
    print(f"[PROCESS] Background processing completed in {t_processing:.2f}s")
    
    # 3. Verify Metadata & Analysis
    meta_res = client.get(f"/api/projects/{project_id}")
    assert meta_res.status_code == 200
    meta = meta_res.json()
    print(f"[METADATA] Total files: {meta['total_files']}, Total LOC: {meta['total_lines_of_code']}, Languages: {meta['languages']}")
    
    # 4. Verify AST analysis
    ast_res = client.get(f"/api/projects/{project_id}/analyze")
    assert ast_res.status_code == 200
    ast_data = ast_res.json()
    print(f"[AST] Analyzed {len(ast_data['files_analyzed'])} AST files, {ast_data['total_classes']} classes, {ast_data['total_functions']} functions")
    
    # 5. Verify Dependency Graph
    dep_res = client.get(f"/api/projects/{project_id}/dependencies")
    assert dep_res.status_code == 200
    dep_data = dep_res.json()
    print(f"[DEPS] Generated graph with {len(dep_data['nodes'])} nodes, {len(dep_data['edges'])} edges")
    
    # Cleanup
    del_res = client.delete(f"/api/projects/{project_id}")
    assert del_res.status_code == 200
    print(f"[CLEANUP] Workspace cleaned up successfully")
    print(f"[RESULT] {label} TEST PASSED (Upload: {t_upload:.3f}s | Processing: {t_processing:.2f}s)")
    return True

if __name__ == "__main__":
    print("==================================================")
    print("STARTING INCREMENTAL ZIP UPLOAD STRESS TESTS")
    print("==================================================")
    
    # Test 1: 1 MB ZIP
    test_zip_upload_size("1 MB ZIP", 1.0)
    
    # Test 2: 10 MB ZIP
    test_zip_upload_size("10 MB ZIP", 10.0)
    
    # Test 3: 50 MB ZIP
    test_zip_upload_size("50 MB ZIP", 50.0)
    
    # Test 4: 135 MB ZIP (Matches the production failure case of 130.7 MB)
    test_zip_upload_size("135 MB ZIP (Production Target)", 135.0)
    
    print("\n" + "=" * 50)
    print("ALL 4 INCREMENTAL TESTS (1MB, 10MB, 50MB, 135MB) PASSED!")
    print("==================================================")
