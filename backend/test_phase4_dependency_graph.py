import os
import zipfile
import io
import json
from fastapi.testclient import TestClient
from app.main import app
from app.celery_app import celery_app

celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True

client = TestClient(app)

def create_realistic_django_test_zip() -> bytes:
    """Creates a realistic Django-style Python project ZIP containing all 15 test scenarios."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # File 1: main.py
        # Test 1: import local_module (import views)
        # Test 6: import os
        # Test 7: import json
        # Test 8: from django.http import HttpResponse
        # Test 9: import requests
        # Test 13: import completely_unknown_module_xyz
        # Duplicate imports (import os twice or from django.http import HttpResponse twice)
        main_py = '''import os
import json
import views
from django.http import HttpResponse
import requests
import completely_unknown_module_xyz
import os  # Duplicate import test

def entrypoint():
    print("Main app entrypoint")
'''
        zf.writestr("main.py", main_py)

        # File 2: views.py
        # Test 2: from local_module import function (from models import User)
        # Test 3: from package.module import function (from services.payment import process_payment)
        # Test 10: from PIL import Image
        # Test 11: from docx import Document
        # Test 12: import fitz
        views_py = '''from models import User
from services.payment import process_payment
from PIL import Image
from docx import Document
import fitz

def render_view():
    return User()
'''
        zf.writestr("views.py", views_py)

        # File 3: models.py
        # Test 4: from .utils import helper (relative import)
        models_py = '''from .utils import helper

class User:
    pass
'''
        zf.writestr("models.py", models_py)

        # File 4: utils.py
        utils_py = '''def helper():
    return "OK"
'''
        zf.writestr("utils.py", utils_py)

        # File 5: services/__init__.py
        zf.writestr("services/__init__.py", "# Services package init")

        # File 6: services/payment.py
        # Test 5: from ..utils import helper (parent relative import test in nested package)
        # Test 14: Circular dependency setup (services/payment.py imports circular_a.py)
        payment_py = '''from ..utils import helper
import circular_a

def process_payment(amount):
    return helper()
'''
        zf.writestr("services/payment.py", payment_py)

        # File 7: circular_a.py
        # Test 14: Circular dependency (circular_a.py -> circular_b.py)
        circ_a_py = '''import circular_b

def func_a():
    return circular_b.func_b()
'''
        zf.writestr("circular_a.py", circ_a_py)

        # File 8: circular_b.py
        # Test 14: Circular dependency (circular_b.py -> circular_a.py)
        circ_b_py = '''import circular_a

def func_b():
    return circular_a.func_a()
'''
        zf.writestr("circular_b.py", circ_b_py)

    return zip_buffer.getvalue()


def test_phase4_dependency_classification():
    print("=== Testing Phase 4 Dependency Graph & 3-Category Classification Engine ===")

    # Upload test ZIP
    zip_bytes = create_realistic_django_test_zip()
    res_upload = client.post(
        "/api/projects/upload",
        files={"file": ("django_sample_project.zip", zip_bytes, "application/zip")}
    )
    assert res_upload.status_code in (201, 202), f"Upload failed: {res_upload.text}"
    project_id = res_upload.json()["project_id"]
    print(f"[PASS] Setup: Uploaded test project ZIP. Project ID: {project_id}")

    # Call GET /api/projects/{project_id}/dependencies
    res_dep = client.get(f"/api/projects/{project_id}/dependencies")
    assert res_dep.status_code == 200, f"Dependency API failed: {res_dep.text}"
    graph_data = res_dep.json()

    nodes = graph_data["nodes"]
    edges = graph_data["edges"]
    ext_libs = graph_data["external_libraries"]
    unresolved = graph_data["unresolved_imports"]
    edge_pairs = {(e["source"], e["target"]) for e in edges}
    ext_lib_names = {lib["name"] for lib in ext_libs}

    print(f"\nExtracted {len(nodes)} project file nodes and {len(edges)} project dependency edges.")
    print(f"Extracted {len(ext_libs)} external libraries: {sorted(list(ext_lib_names))}")
    print(f"Extracted {len(unresolved)} unresolved imports: {unresolved}\n")

    # TEST 1: import local_module (main.py -> views.py)
    assert ("main.py", "views.py") in edge_pairs
    print("[PASS] TEST 1: import local_module -> PROJECT DEPENDENCY (main.py -> views.py)")

    # TEST 2: from local_module import function (views.py -> models.py)
    assert ("views.py", "models.py") in edge_pairs
    print("[PASS] TEST 2: from local_module import function -> PROJECT DEPENDENCY (views.py -> models.py)")

    # TEST 3: from package.module import function (views.py -> services/payment.py)
    assert ("views.py", "services/payment.py") in edge_pairs
    print("[PASS] TEST 3: from package.module import function -> PROJECT DEPENDENCY (views.py -> services/payment.py)")

    # TEST 4: from .utils import helper (models.py -> utils.py)
    assert ("models.py", "utils.py") in edge_pairs
    print("[PASS] TEST 4: from .utils import helper -> PROJECT DEPENDENCY (models.py -> utils.py)")

    # TEST 5: from ..utils import helper (services/payment.py -> utils.py)
    assert ("services/payment.py", "utils.py") in edge_pairs
    print("[PASS] TEST 5: from ..utils import helper -> PROJECT DEPENDENCY (services/payment.py -> utils.py)")

    # TEST 6: import os -> EXTERNAL / STANDARD LIBRARY
    assert "Standard Library" in ext_lib_names
    os_found = any("os" in lib["imports"] for lib in ext_libs if lib["name"] == "Standard Library")
    assert os_found, "os not found in Standard Library imports"
    print("[PASS] TEST 6: import os -> EXTERNAL / STANDARD LIBRARY")

    # TEST 7: import json -> EXTERNAL / STANDARD LIBRARY
    json_found = any("json" in lib["imports"] for lib in ext_libs if lib["name"] == "Standard Library")
    assert json_found, "json not found in Standard Library imports"
    print("[PASS] TEST 7: import json -> EXTERNAL / STANDARD LIBRARY")

    # TEST 8: from django.http import HttpResponse -> EXTERNAL / THIRD PARTY (Django)
    assert "Django" in ext_lib_names
    django_lib = [l for l in ext_libs if l["name"] == "Django"][0]
    assert any("django.http" in imp for imp in django_lib["imports"])
    print("[PASS] TEST 8: from django.http import HttpResponse -> EXTERNAL / THIRD PARTY (Django)")

    # TEST 9: import requests -> EXTERNAL / THIRD PARTY (Requests)
    assert "Requests" in ext_lib_names
    print("[PASS] TEST 9: import requests -> EXTERNAL / THIRD PARTY (Requests)")

    # TEST 10: from PIL import Image -> EXTERNAL / THIRD PARTY (Pillow)
    assert "Pillow" in ext_lib_names
    print("[PASS] TEST 10: from PIL import Image -> EXTERNAL / THIRD PARTY (Pillow)")

    # TEST 11: from docx import Document -> EXTERNAL / THIRD PARTY (python-docx)
    assert "python-docx" in ext_lib_names
    print("[PASS] TEST 11: from docx import Document -> EXTERNAL / THIRD PARTY (python-docx)")

    # TEST 12: import fitz -> EXTERNAL / THIRD PARTY (PyMuPDF)
    assert "PyMuPDF" in ext_lib_names
    print("[PASS] TEST 12: import fitz -> EXTERNAL / THIRD PARTY (PyMuPDF)")

    # TEST 13: import completely_unknown_module_xyz -> UNRESOLVED
    assert "completely_unknown_module_xyz" in unresolved
    assert "Django" not in unresolved
    assert "Requests" not in unresolved
    assert "Pillow" not in unresolved
    print("[PASS] TEST 13: import completely_unknown_module_xyz -> UNRESOLVED")

    # TEST 14: Circular dependency (circular_a.py <-> circular_b.py)
    assert ("circular_a.py", "circular_b.py") in edge_pairs
    assert ("circular_b.py", "circular_a.py") in edge_pairs
    print("[PASS] TEST 14: Circular dependency (circular_a.py <-> circular_b.py) generated successfully without crashing")

    # TEST 15: Duplicate imports -> No duplicate graph edges
    edge_ids = [e["id"] for e in edges]
    assert len(edge_ids) == len(set(edge_ids)), "Duplicate edge IDs detected!"
    print("[PASS] TEST 15: Duplicate imports -> No duplicate graph edges created")

    # Clean up temporary workspace
    client.delete(f"/api/projects/{project_id}")
    print("[PASS] Cleanup: Temporary project workspace purged successfully")

    print("\nSAMPLE COMPLETED DEPENDENCY GRAPH API RESPONSE SNIPPET:")
    print(json.dumps({
        "project_id": graph_data["project_id"],
        "total_nodes": graph_data["total_nodes"],
        "total_edges": graph_data["total_edges"],
        "nodes_sample": [n["id"] for n in nodes[:4]],
        "edges_sample": [e["id"] for e in edges[:4]],
        "external_libraries": [
            {"name": l["name"], "type": l["type"], "imports": l["imports"]}
            for l in ext_libs
        ],
        "unresolved_imports": unresolved
    }, indent=2))

    print("\nALL 15 PHASE 4 CLASSIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_phase4_dependency_classification()
