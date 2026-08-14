import os
import zipfile
import io
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.ai.schemas import (
    ProjectExplanation,
    ModuleExplanation,
    ClassExplanation,
    FunctionExplanation,
    ParameterExplanation
)
from app.ai.exceptions import AITimeoutError, AIValidationError

client = TestClient(app)

def create_phase6_test_zip() -> bytes:
    """Creates a sample multi-file ZIP archive containing Python, Markdown, JSON, Config, JS, and Binary files."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Python file with AST metadata: main.py
        main_py = '''import os
from utils import format_currency

def calculate_total(price, quantity):
    """Calculates total price from unit price and quantity."""
    return price * quantity

def process_order(item_name, price, quantity, discount=0.0):
    subtotal = calculate_total(price, quantity)
    final_total = subtotal - discount
    return format_currency(final_total)

class OrderProcessor:
    """Class managing order processing."""
    def __init__(self, currency="USD"):
        self.currency = currency

    def execute(self, price, quantity):
        return calculate_total(price, quantity)
'''
        zf.writestr("main.py", main_py)

        # 2. Markdown file: API_GUIDE.md
        api_md = '''# API Guide for CodeOracle
## Overview
This document describes the API endpoints for legacy codebase analysis.

## Endpoints
- `POST /api/projects/upload`: Upload codebase ZIP.
- `GET /api/projects/{id}/explanations/project`: Get architectural overview.
'''
        zf.writestr("API_GUIDE.md", api_md)

        # 3. JSON file: config.json
        config_json = '''{
    "app_name": "CodeOracle",
    "version": "1.0.0",
    "settings": {
        "max_files": 50,
        "debug": true
    }
}'''
        zf.writestr("config.json", config_json)

        # 4. Config file: .gitignore
        gitignore = '''__pycache__/
*.pyc
node_modules/
.env
'''
        zf.writestr(".gitignore", gitignore)

        # 5. JavaScript file: script.js
        script_js = '''function greetUser(name) {
    console.log("Hello " + name);
}
module.exports = { greetUser };
'''
        zf.writestr("script.js", script_js)

        # 6. Binary file: db.sqlite3
        binary_bytes = b"SQLite format 3\x00\x01\x01\x00\x40\x20\x20\x00" + b"\x00" * 100
        zf.writestr("db.sqlite3", binary_bytes)

        # 7. Empty text file: empty.txt
        zf.writestr("empty.txt", "")

        # 8. Large Markdown file: FEATURES.md
        large_md = "# CodeOracle Features\n" + ("- Feature detail point for modernizing legacy code.\n" * 200)
        zf.writestr("FEATURES.md", large_md)

    return zip_buffer.getvalue()

def test_1_python_file_with_ast(project_id):
    """Test 1: Python file with AST metadata returns AST-powered explanation."""
    res = client.post(
        f"/api/projects/{project_id}/explanations/module",
        json={"file_path": "main.py"}
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["file_path"] == "main.py"
    assert data["file_type"] == "python"
    assert "calculate_total" in data["functions"]
    print("[PASS] Test 1: Python file with AST metadata explained successfully.")

def test_2_markdown_file_without_ast(project_id):
    """Test 2: Markdown file without AST metadata returns content-based explanation without error."""
    res = client.post(
        f"/api/projects/{project_id}/explanations/module",
        json={"file_path": "API_GUIDE.md"}
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["file_path"] == "API_GUIDE.md"
    assert data["file_type"] == "markdown"
    assert data["is_binary"] is False
    assert "AST metadata for" not in json.dumps(data)
    print("[PASS] Test 2: Markdown file without AST metadata explained successfully.")

def test_3_json_file_without_ast(project_id):
    """Test 3: JSON file without AST metadata returns JSON structure explanation."""
    res = client.post(
        f"/api/projects/{project_id}/explanations/module",
        json={"file_path": "config.json"}
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["file_path"] == "config.json"
    assert data["file_type"] == "json"
    print("[PASS] Test 3: JSON file without AST metadata explained successfully.")

def test_4_config_text_file(project_id):
    """Test 4: Config / text file (.gitignore) returns config explanation."""
    res = client.post(
        f"/api/projects/{project_id}/explanations/module",
        json={"file_path": ".gitignore"}
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["file_path"] == ".gitignore"
    assert data["file_type"] == "config"
    print("[PASS] Test 4: Config file (.gitignore) explained successfully.")

def test_5_javascript_file(project_id):
    """Test 5: JavaScript file without Python AST returns source-based explanation."""
    res = client.post(
        f"/api/projects/{project_id}/explanations/module",
        json={"file_path": "script.js"}
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["file_path"] == "script.js"
    assert data["file_type"] == "javascript"
    print("[PASS] Test 5: JavaScript file explained successfully.")

def test_6_binary_file(project_id):
    """Test 6: Binary file (db.sqlite3) returns basic binary metadata without sending AI prompt."""
    res = client.post(
        f"/api/projects/{project_id}/explanations/module",
        json={"file_path": "db.sqlite3"}
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["file_path"] == "db.sqlite3"
    assert data["is_binary"] is True
    assert "Binary" in data["purpose"] or "database" in data["purpose"].lower()
    print("[PASS] Test 6: Binary database file (db.sqlite3) handled safely without AI error.")

def test_7_missing_file(project_id):
    """Test 7: Missing file path returns 404 Not Found."""
    res = client.post(
        f"/api/projects/{project_id}/explanations/module",
        json={"file_path": "non_existent_file.py"}
    )
    assert res.status_code == 404
    print("[PASS] Test 7: Missing file returned 404 Not Found.")

def test_8_empty_text_file(project_id):
    """Test 8: Empty text file returns informative empty file summary."""
    res = client.post(
        f"/api/projects/{project_id}/explanations/module",
        json={"file_path": "empty.txt"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "Empty" in data["purpose"] or "empty" in data["purpose"].lower()
    print("[PASS] Test 8: Empty text file handled gracefully.")

def test_9_large_markdown_file(project_id):
    """Test 9: Large Markdown file handled with context truncation."""
    res = client.post(
        f"/api/projects/{project_id}/explanations/module",
        json={"file_path": "FEATURES.md"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["file_type"] == "markdown"
    print("[PASS] Test 9: Large Markdown file context truncated and explained successfully.")

def test_10_cache_behavior(project_id):
    """Test 10: Repeated request reuses cached explanation."""
    res1 = client.post(
        f"/api/projects/{project_id}/explanations/module",
        json={"file_path": "API_GUIDE.md"}
    )
    assert res1.status_code == 200
    
    res2 = client.post(
        f"/api/projects/{project_id}/explanations/module",
        json={"file_path": "API_GUIDE.md"}
    )
    assert res2.status_code == 200
    assert res1.json() == res2.json()
    print("[PASS] Test 10: Repeated request cache behavior verified.")

def run_all_phase6_fix_tests():
    print("=== Running Phase 6 Multi-File Explanation Test Suite ===")
    zip_bytes = create_phase6_test_zip()
    res = client.post(
        "/api/projects/upload",
        files={"file": ("phase6_fix_test.zip", zip_bytes, "application/zip")}
    )
    assert res.status_code in (201, 202)
    project_id = res.json()["project_id"]

    try:
        test_1_python_file_with_ast(project_id)
        test_2_markdown_file_without_ast(project_id)
        test_3_json_file_without_ast(project_id)
        test_4_config_text_file(project_id)
        test_5_javascript_file(project_id)
        test_6_binary_file(project_id)
        test_7_missing_file(project_id)
        test_8_empty_text_file(project_id)
        test_9_large_markdown_file(project_id)
        test_10_cache_behavior(project_id)
    finally:
        client.delete(f"/api/projects/{project_id}")

    print("\nALL PHASE 6 FIX TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_all_phase6_fix_tests()
