import os
import json
import pytest
import tempfile
import zipfile
from fastapi.testclient import TestClient

from app.main import app
from app.celery_app import celery_app
from app.tasks import (
    process_project_task,
    process_github_project_task,
    dispatch_project_processing
)
from app.services.extractor import (
    init_project_workspace,
    get_project_status,
    get_project_directory
)

client = TestClient(app)

@pytest.fixture(autouse=True)
def configure_celery_for_tests():
    """Configures Celery to run in eager test mode during unit tests."""
    orig_eager = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = orig_eager

@pytest.fixture
def sample_zip():
    with tempfile.TemporaryDirectory() as td:
        src_dir = os.path.join(td, "src")
        os.makedirs(src_dir, exist_ok=True)
        with open(os.path.join(src_dir, "calc.py"), "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a + b\n")
        with open(os.path.join(src_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write("from calc import add\nprint(add(2, 3))\n")

        zip_path = os.path.join(td, "test_celery.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            for fname in os.listdir(src_dir):
                zf.write(os.path.join(src_dir, fname), fname)

        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        yield zip_bytes, "test_celery.zip"


def test_celery_app_configuration():
    """Test 1: Celery application configuration adheres to architectural standards."""
    assert celery_app.main == "codeoracle"
    assert celery_app.conf.task_serializer == "json"
    assert "json" in celery_app.conf.accept_content
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.timezone == "UTC"


def test_celery_process_project_task(sample_zip):
    """Test 2: Celery task executes extraction, AST parsing, and graph generation."""
    zip_bytes, fname = sample_zip
    pid, pdir, zip_path = init_project_workspace(fname)
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)

    # Execute task synchronously as unit test
    result = process_project_task.run(pid, fname)
    assert result["status"] == "completed"

    # Verify status.json updated to completed (100%)
    status_data = get_project_status(pid)
    assert status_data.status == "completed"
    assert status_data.progress == 100

    # Verify metadata and dependency graph created
    assert os.path.exists(os.path.join(pdir, "project_metadata.json"))
    assert os.path.exists(os.path.join(pdir, "analysis_ast.json"))
    assert os.path.exists(os.path.join(pdir, "dependency_graph.json"))


def test_celery_task_non_retryable_corrupt_zip():
    """Test 3: Corrupted ZIP files fail cleanly without infinite retries."""
    pid, pdir, zip_path = init_project_workspace("corrupt.zip")
    with open(zip_path, "wb") as f:
        f.write(b"not a valid zip file content")

    result = process_project_task.run(pid, "corrupt.zip")
    assert result["status"] == "failed"

    status_data = get_project_status(pid)
    assert status_data.status == "failed"


def test_upload_endpoint_returns_202_accepted(sample_zip):
    """Test 4: POST /api/projects/upload returns HTTP 202 Accepted without blocking."""
    zip_bytes, fname = sample_zip
    res = client.post(
        "/api/projects/upload",
        files={"file": (fname, zip_bytes, "application/zip")}
    )
    assert res.status_code == 202
    data = res.json()
    assert "project_id" in data
    assert data["status"] == "queued"
    assert "Processing started" in data["message"]


def test_celery_task_js_ts_and_python():
    """Test 5: Celery task processes mixed Python, JavaScript, and TypeScript projects."""
    with tempfile.TemporaryDirectory() as td:
        src_dir = os.path.join(td, "src")
        os.makedirs(src_dir, exist_ok=True)
        with open(os.path.join(src_dir, "server.py"), "w", encoding="utf-8") as f:
            f.write("def start_server():\n    return True\n")
        with open(os.path.join(src_dir, "App.jsx"), "w", encoding="utf-8") as f:
            f.write("import React from 'react';\nexport default function App() { return <div>Hello</div>; }\n")
        with open(os.path.join(src_dir, "types.ts"), "w", encoding="utf-8") as f:
            f.write("export interface User { id: string; name: string; }\n")

        zip_path = os.path.join(td, "mixed.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            for fname in os.listdir(src_dir):
                zf.write(os.path.join(src_dir, fname), fname)

        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

    pid, pdir, zip_path = init_project_workspace("mixed.zip")
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)

    result = process_project_task.run(pid, "mixed.zip")
    assert result["status"] == "completed"

    status_data = get_project_status(pid)
    assert status_data.status == "completed"
    assert status_data.progress == 100

    meta_path = os.path.join(pdir, "project_metadata.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
        assert meta["total_files"] == 3
        assert "Python" in meta["languages"]
        assert any("JavaScript" in lang for lang in meta["languages"])
        assert "TypeScript" in meta["languages"]
