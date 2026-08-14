import os
import json
import pytest
import tempfile
from fastapi.testclient import TestClient

from app.main import app
from app.services.extractor import create_project_workspace
from app.services.improvements_service import (
    compute_deterministic_improvements,
    explain_improvements_with_ai
)

client = TestClient(app)

@pytest.fixture
def clean_project():
    """Project with clean, concise code."""
    with tempfile.TemporaryDirectory() as td:
        src_dir = os.path.join(td, "src")
        os.makedirs(src_dir, exist_ok=True)
        with open(os.path.join(src_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write("def add(a: int, b: int) -> int:\n    return a + b\n")
        import zipfile
        zip_path = os.path.join(td, "clean.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(os.path.join(src_dir, "main.py"), "main.py")
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        from app.services.extractor import extract_zip_file
        meta = extract_zip_file(zip_bytes, "clean.zip")
        from app.services.extractor import get_project_directory
        pdir = get_project_directory(meta.project_id)
        yield meta.project_id, pdir

@pytest.fixture
def complex_project():
    """Project with large function, deep nesting, unused imports, and high coupling."""
    with tempfile.TemporaryDirectory() as td:
        src_dir = os.path.join(td, "src")
        os.makedirs(src_dir, exist_ok=True)
        # File 1: main.py with large function and unused import
        with open(os.path.join(src_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write(
                "import os\nimport math\nfrom utils import helper\n\n"
                "def very_long_function(a, b, c, d, e):\n"
                "    total = 0\n" +
                "\n".join([f"    total += {i}" for i in range(50)]) +
                "\n    if a:\n        if b:\n            if c:\n                if d:\n                    return total\n"
                "    return total\n"
            )
        # File 2: utils.py (hub)
        with open(os.path.join(src_dir, "utils.py"), "w", encoding="utf-8") as f:
            f.write("def helper():\n    return 42\n")

        # Files 3..8 importing utils.py (creating hub)
        for i in range(7):
            with open(os.path.join(src_dir, f"service_{i}.py"), "w", encoding="utf-8") as f:
                f.write(f"from utils import helper\ndef run_{i}():\n    return helper()\n")

        import zipfile
        zip_path = os.path.join(td, "complex.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            for fname in os.listdir(src_dir):
                if fname.endswith(".py"):
                    zf.write(os.path.join(src_dir, fname), fname)
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        from app.services.extractor import extract_zip_file
        meta = extract_zip_file(zip_bytes, "complex.zip")
        from app.services.extractor import get_project_directory
        pdir = get_project_directory(meta.project_id)
        yield meta.project_id, pdir


def test_clean_project_improvements(clean_project):
    """Test 1: Project with minimal issues returns verified accomplishments and high score."""
    pid, _ = clean_project
    res = client.get(f"/api/projects/{pid}/improvements")
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == pid
    assert data["health_metrics"]["code_quality_pct"] >= 80
    assert len(data["already_done_well"]) > 0


def test_complex_project_improvements(complex_project):
    """Test 2: Project with large functions, nesting, and dependency hubs."""
    pid, _ = complex_project
    res = client.get(f"/api/projects/{pid}/improvements")
    assert res.status_code == 200
    data = res.json()
    assert data["total_recommendations"] > 0
    categories = data["categories_present"]
    assert "LARGE_FUNCTIONS" in categories or "COMPLEXITY" in categories
    assert data["evidence_count"] > 0


def test_evidence_structure_integrity(complex_project):
    """Test 3: Every recommendation must contain structured evidence matching real files."""
    pid, _ = complex_project
    res = client.get(f"/api/projects/{pid}/improvements")
    assert res.status_code == 200
    data = res.json()
    for rec in data["recommendations"]:
        assert rec["id"] is not None
        assert rec["title"] is not None
        assert rec["why_it_matters"] is not None
        assert rec["action"] is not None
        assert len(rec["evidence"]) > 0
        for ev in rec["evidence"]:
            assert ev["file"] is not None
            assert ev["metric"] is not None


def test_coverage_gap_recommendation(clean_project):
    """Test 4: Coverage gaps produce targeted evidence recommendations."""
    pid, pdir = clean_project
    # Inject fake coverage cache
    cache_path = os.path.join(pdir, "explanation_cache.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({
            "coverage": {
                "coverage_percentage": 45.0,
                "files": [{
                    "file": "main.py",
                    "coverage_percentage": 45.0,
                    "statements": 20,
                    "missing_lines": [2, 3, 4]
                }]
            }
        }, f)

    res = client.get(f"/api/projects/{pid}/improvements")
    assert res.status_code == 200
    data = res.json()
    assert "TEST_COVERAGE" in data["categories_present"]
    cov_rec = next(r for r in data["recommendations"] if r["category"] == "TEST_COVERAGE")
    assert "45" in cov_rec["title"] or "main.py" in cov_rec["title"]


def test_missing_project_404():
    """Test 5: Missing project ID returns HTTP 404."""
    res = client.get("/api/projects/non_existent_id_9999/improvements")
    assert res.status_code == 404


def test_ai_explanation_endpoint_graceful_fallback(complex_project):
    """Test 6: POST /explain endpoint returns valid response even if AI provider is mocked/fallback."""
    pid, _ = complex_project
    res = client.post(f"/api/projects/{pid}/improvements/explain", json={})
    assert res.status_code == 200
    data = res.json()
    assert "health_metrics" in data
    assert "recommendations" in data
