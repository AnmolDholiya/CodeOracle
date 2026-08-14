import os
import zipfile
import io
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_sample_ast_zip() -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # File 1: main.py
        main_py = '''import os
from models.user import User
from services.calculator import Calculator, add_numbers

def run_app(user_name: str = "Admin") -> None:
    """Runs the main application entrypoint."""
    user = User(name=user_name, user_id=101)
    calc = Calculator(precision=2)
    res = calc.add(10.5, 20.5)
    print(f"User {user.name} result: {res}")

if __name__ == "__main__":
    run_app()
'''
        zf.writestr("main.py", main_py)

        # File 2: models/user.py
        user_py = '''from typing import Optional

class BaseEntity:
    """Base entity for database models."""
    def get_id(self) -> int:
        return getattr(self, "id", 0)

class User(BaseEntity):
    """User account entity."""
    def __init__(self, name: str, user_id: int, email: Optional[str] = None):
        self.name = name
        self.id = user_id
        self.email = email

    def format_display_name(self) -> str:
        return f"{self.name} <{self.email}>" if self.email else self.name
'''
        zf.writestr("models/user.py", user_py)

        # File 3: services/calculator.py
        calc_py = '''import math as m

def add_numbers(a: float, b: float = 0.0) -> float:
    """Standalone math function."""
    return a + b

class Calculator:
    """Mathematical calculations service."""
    def __init__(self, precision: int = 2):
        self.precision = precision

    def add(self, x: float, y: float) -> float:
        val = add_numbers(x, y)
        return round(val, self.precision)

    def square_root(self, val: float) -> float:
        return m.sqrt(val)
'''
        zf.writestr("services/calculator.py", calc_py)

        # File 4: invalid_syntax.py (Malformed Python File for Error Handling Test)
        invalid_py = '''def broken_function(:
    print("This file has invalid syntax"
'''
        zf.writestr("invalid_syntax.py", invalid_py)

    return zip_buffer.getvalue()


def test_phase3_ast_analysis():
    print("=== Testing Phase 3 Python AST Analysis Engine ===")

    # 1. Create and Upload Sample ZIP Archive
    zip_bytes = create_sample_ast_zip()
    res_upload = client.post(
        "/api/projects/upload",
        files={"file": ("sample_ast_project.zip", zip_bytes, "application/zip")}
    )
    assert res_upload.status_code in (201, 202), f"Upload failed: {res_upload.text}"
    upload_data = res_upload.json()
    project_id = upload_data["project_id"]
    print(f"[PASS] 1. Uploaded sample AST project ZIP. Project ID: {project_id}")

    # 2. Call POST /api/projects/{project_id}/analyze
    res_analyze = client.post(f"/api/projects/{project_id}/analyze")
    assert res_analyze.status_code == 200, f"Analysis endpoint failed: {res_analyze.text}"
    analysis = res_analyze.json()

    print(f"[PASS] 2. POST /api/projects/{project_id}/analyze executed successfully")
    print(f"       Total Python Files Analyzed: {analysis['total_python_files']}")
    print(f"       Total Lines of Code: {analysis['total_lines_of_code']}")
    print(f"       Total Classes Extracted: {analysis['total_classes']}")
    print(f"       Total Functions Extracted: {analysis['total_functions']}")
    print(f"       Total Imports Extracted: {analysis['total_imports']}")

    # Check extracted details across files
    files_by_name = {f["relative_path"]: f for f in analysis["files_analyzed"]}

    # Verify main.py
    assert "main.py" in files_by_name
    main_ast = files_by_name["main.py"]
    assert len(main_ast["imports"]) == 4
    assert main_ast["imports"][0]["module"] == "os"
    assert main_ast["imports"][1]["module"] == "models.user"
    assert main_ast["imports"][1]["name"] == "User"
    assert len(main_ast["functions"]) == 1
    func_run = main_ast["functions"][0]
    assert func_run["name"] == "run_app"
    assert func_run["parameters"][0]["name"] == "user_name"
    assert func_run["parameters"][0]["default"] == "'Admin'"
    assert "User" in func_run["calls"]
    assert "Calculator" in func_run["calls"]
    assert "calc.add" in func_run["calls"]
    print("[PASS] 3. Verified main.py AST (Imports, Functions, Parameters, Function Calls)")

    # Verify models/user.py (Inheritance & Classes)
    assert "models/user.py" in files_by_name
    user_ast = files_by_name["models/user.py"]
    assert len(user_ast["classes"]) == 2
    class_user = [c for c in user_ast["classes"] if c["name"] == "User"][0]
    assert class_user["bases"] == ["BaseEntity"]
    assert len(class_user["methods"]) == 2
    print("[PASS] 4. Verified models/user.py AST (Class Inheritance & Methods)")

    # Verify services/calculator.py (Standalone Functions & Class Methods)
    assert "services/calculator.py" in files_by_name
    calc_ast = files_by_name["services/calculator.py"]
    assert len(calc_ast["functions"]) == 1
    assert calc_ast["functions"][0]["name"] == "add_numbers"
    class_calc = calc_ast["classes"][0]
    assert class_calc["name"] == "Calculator"
    method_add = [m for m in class_calc["methods"] if m["name"] == "add"][0]
    assert "add_numbers" in method_add["calls"]
    assert "round" in method_add["calls"]
    print("[PASS] 5. Verified services/calculator.py AST (Functions, Class Methods, Nested Calls)")

    # Verify Error Handling for invalid_syntax.py
    assert "invalid_syntax.py" in files_by_name
    invalid_ast = files_by_name["invalid_syntax.py"]
    assert invalid_ast["has_syntax_error"] is True
    assert "Syntax error" in invalid_ast["syntax_error_message"]
    print(f"[PASS] 6. Graceful Error Handling Verified for invalid_syntax.py: {invalid_ast['syntax_error_message']}")

    # 3. Verify GET /api/projects/{project_id}/analyze returns cached result
    res_get = client.get(f"/api/projects/{project_id}/analyze")
    assert res_get.status_code == 200
    assert res_get.json()["total_python_files"] == analysis["total_python_files"]
    print("[PASS] 7. GET /api/projects/{project_id}/analyze returned valid cached JSON")

    # 4. Clean up temporary project
    client.delete(f"/api/projects/{project_id}")
    print("[PASS] 8. Temporary workspace cleaned up")

    print("\nSAMPLE ANALYSIS JSON OUTPUT SNIPPET:")
    # Print a nicely formatted snippet of the analysis result for validation
    print(json.dumps(analysis, indent=2))

if __name__ == "__main__":
    test_phase3_ast_analysis()
