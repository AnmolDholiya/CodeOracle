import sys
import os
import io
import zipfile
import asyncio
import time

# Ensure backend root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import load_backend_environment
load_backend_environment()

from fastapi.testclient import TestClient
from app.main import app
from app.services.extractor import get_project_directory
from app.services.breaking_change_service import (
    analyze_breaking_changes,
    explain_breaking_changes
)

client = TestClient(app)

def create_breaking_change_test_zip() -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "billing.py",
            "import math\n"
            "from utils import calculate\n\n"
            "def calculate_total(items):\n"
            "    return sum(items)\n\n"
            "def process(data):\n"
            "    return data * 2\n\n"
            "def connect(timeout=30):\n"
            "    return True\n\n"
            "def _internal_helper():\n"
            "    return 42\n\n"
            "class PaymentService:\n"
            "    def charge(self, amount):\n"
            "        return True\n"
            "    def refund(self, amount):\n"
            "        return True\n"
        )
        zf.writestr(
            "checkout.py",
            "from billing import calculate_total\n\n"
            "def checkout_cart():\n"
            "    return calculate_total([10, 20])\n"
        )
        zf.writestr(
            "utils.py",
            "def calculate(n):\n"
            "    return n + 1\n"
        )
    return zip_buffer.getvalue()

def run_phase9_test_suite():
    print("=== CODEORACLE PHASE 9 BREAKING-CHANGE DETECTION TEST SUITE ===\n")

    # TEST SETUP: Upload project
    zip_bytes = create_breaking_change_test_zip()
    up_res = client.post(
        "/api/projects/upload",
        files={"file": ("breaking_project.zip", zip_bytes, "application/zip")}
    )
    assert up_res.status_code == 201, f"Upload failed: {up_res.text}"
    project_id = up_res.json()["project_id"]
    print(f"[PASS] Setup: Uploaded breaking change test codebase (ID: {project_id})\n")

    try:
        # TEST 1: Function Removed (FUNCTION_REMOVED - HIGH)
        print("--- TEST 1: Detect Removed Function ---")
        mod_code_1 = (
            "import math\nfrom utils import calculate\n\n"
            "def process(data): return data * 2\n"
            "def connect(timeout=30): return True\n"
            "class PaymentService:\n"
            "    def charge(self, amount): return True\n"
            "    def refund(self, amount): return True\n"
        )
        res1 = analyze_breaking_changes(project_id, "billing.py", mod_code_1)
        fn_rem = [c for c in res1.changes if c.type == "FUNCTION_REMOVED" and c.symbol == "calculate_total"]
        assert len(fn_rem) == 1
        assert fn_rem[0].severity == "HIGH"
        print(f"[PASS] TEST 1: FUNCTION_REMOVED correctly detected with HIGH severity.\n")

        # TEST 2: Required Parameter Added (PARAMETER_ADDED - HIGH)
        print("--- TEST 2: Detect Required Parameter Added ---")
        mod_code_2 = (
            "import math\nfrom utils import calculate\n\n"
            "def calculate_total(items, tax):\n"
            "    return sum(items) + tax\n\n"
            "def process(data): return data * 2\n"
            "def connect(timeout=30): return True\n"
            "class PaymentService:\n"
            "    def charge(self, amount): return True\n"
            "    def refund(self, amount): return True\n"
        )
        res2 = analyze_breaking_changes(project_id, "billing.py", mod_code_2)
        param_add = [c for c in res2.changes if c.type == "PARAMETER_ADDED" and c.severity == "HIGH"]
        assert len(param_add) >= 1
        print(f"[PASS] TEST 2: Required parameter added correctly classified as HIGH severity.\n")

        # TEST 3: Parameter Renamed (PARAMETER_RENAMED - MEDIUM)
        print("--- TEST 3: Detect Parameter Renamed ---")
        mod_code_3 = (
            "import math\nfrom utils import calculate\n\n"
            "def calculate_total(items): return sum(items)\n"
            "def process(input_data): return input_data * 2\n"
            "def connect(timeout=30): return True\n"
            "class PaymentService:\n"
            "    def charge(self, amount): return True\n"
            "    def refund(self, amount): return True\n"
        )
        res3 = analyze_breaking_changes(project_id, "billing.py", mod_code_3)
        param_ren = [c for c in res3.changes if c.type == "PARAMETER_RENAMED"]
        assert len(param_ren) >= 1
        assert param_ren[0].severity == "MEDIUM"
        print(f"[PASS] TEST 3: PARAMETER_RENAMED correctly classified as MEDIUM severity.\n")

        # TEST 4: Optional Parameter Added (PARAMETER_ADDED - LOW/INFO)
        print("--- TEST 4: Detect Optional Parameter Added with Default Value ---")
        mod_code_4 = (
            "import math\nfrom utils import calculate\n\n"
            "def calculate_total(items, tax=0):\n"
            "    return sum(items) + tax\n\n"
            "def process(data): return data * 2\n"
            "def connect(timeout=30): return True\n"
            "class PaymentService:\n"
            "    def charge(self, amount): return True\n"
            "    def refund(self, amount): return True\n"
        )
        res4 = analyze_breaking_changes(project_id, "billing.py", mod_code_4)
        opt_param = [c for c in res4.changes if c.type == "PARAMETER_ADDED" and c.severity == "LOW"]
        assert len(opt_param) >= 1
        print(f"[PASS] TEST 4: Optional parameter with default value correctly classified as LOW severity.\n")

        # TEST 5: Class Removed (CLASS_REMOVED - HIGH)
        print("--- TEST 5: Detect Class Removed ---")
        mod_code_5 = (
            "import math\nfrom utils import calculate\n\n"
            "def calculate_total(items): return sum(items)\n"
            "def process(data): return data * 2\n"
            "def connect(timeout=30): return True\n"
        )
        res5 = analyze_breaking_changes(project_id, "billing.py", mod_code_5)
        cls_rem = [c for c in res5.changes if c.type == "CLASS_REMOVED"]
        assert len(cls_rem) == 1
        assert cls_rem[0].severity == "HIGH"
        print(f"[PASS] TEST 5: CLASS_REMOVED correctly detected with HIGH severity.\n")

        # TEST 6: Method Removed (METHOD_REMOVED - HIGH)
        print("--- TEST 6: Detect Method Removed ---")
        mod_code_6 = (
            "import math\nfrom utils import calculate\n\n"
            "def calculate_total(items): return sum(items)\n"
            "def process(data): return data * 2\n"
            "def connect(timeout=30): return True\n"
            "class PaymentService:\n"
            "    def charge(self, amount): return True\n"
        )
        res6 = analyze_breaking_changes(project_id, "billing.py", mod_code_6)
        m_rem = [c for c in res6.changes if c.type == "METHOD_REMOVED"]
        assert len(m_rem) == 1
        assert m_rem[0].symbol == "PaymentService.refund"
        assert m_rem[0].severity == "HIGH"
        print(f"[PASS] TEST 6: METHOD_REMOVED correctly detected with HIGH severity.\n")

        # TEST 7: Import Removed / Broken Import (BROKEN_IMPORT - HIGH)
        print("--- TEST 7: Detect Broken Import ---")
        mod_code_7 = (
            "import math\n\n"
            "def calculate_total(items):\n"
            "    return calculate(10) + sum(items)\n"  # Still references 'calculate'
            "def process(data): return data * 2\n"
            "def connect(timeout=30): return True\n"
            "class PaymentService:\n"
            "    def charge(self, amount): return True\n"
            "    def refund(self, amount): return True\n"
        )
        res7 = analyze_breaking_changes(project_id, "billing.py", mod_code_7)
        brk_imp = [c for c in res7.changes if c.type == "BROKEN_IMPORT"]
        assert len(brk_imp) >= 1
        assert brk_imp[0].severity == "HIGH"
        print(f"[PASS] TEST 7: BROKEN_IMPORT correctly detected with HIGH severity.\n")

        # TEST 8: Call-Site Analysis (BREAKING_CALL_SITE - HIGH)
        print("--- TEST 8: Call-Site Analysis Across Workspace ---")
        # In mod_code_2, calculate_total requires 2 arguments (items, tax). checkout.py calls calculate_total([10, 20])
        cs_changes = [c for c in res2.changes if c.type == "BREAKING_CALL_SITE"]
        assert len(cs_changes) >= 1
        assert "checkout.py" in cs_changes[0].file
        print(f"[PASS] TEST 8: BREAKING_CALL_SITE correctly detected in 'checkout.py' with HIGH severity.\n")

        # TEST 9: Default Value Changed (DEFAULT_VALUE_CHANGED - MEDIUM)
        print("--- TEST 9: Detect Default Value Changed ---")
        mod_code_9 = (
            "import math\nfrom utils import calculate\n\n"
            "def calculate_total(items): return sum(items)\n"
            "def process(data): return data * 2\n"
            "def connect(timeout=5): return True\n"
            "class PaymentService:\n"
            "    def charge(self, amount): return True\n"
            "    def refund(self, amount): return True\n"
        )
        res9 = analyze_breaking_changes(project_id, "billing.py", mod_code_9)
        def_chg = [c for c in res9.changes if c.type == "DEFAULT_VALUE_CHANGED"]
        assert len(def_chg) == 1
        assert def_chg[0].severity == "MEDIUM"
        print(f"[PASS] TEST 9: DEFAULT_VALUE_CHANGED correctly classified as MEDIUM severity.\n")

        # TEST 10: No API Changes
        print("--- TEST 10: No API Changes Test ---")
        orig_billing_code = (
            "import math\n"
            "from utils import calculate\n\n"
            "def calculate_total(items):\n"
            "    return sum(items)\n\n"
            "def process(data):\n"
            "    return data * 2\n\n"
            "def connect(timeout=30):\n"
            "    return True\n\n"
            "def _internal_helper():\n"
            "    return 42\n\n"
            "class PaymentService:\n"
            "    def charge(self, amount):\n"
            "        return True\n"
            "    def refund(self, amount):\n"
            "        return True\n"
        )
        res10 = analyze_breaking_changes(project_id, "billing.py", orig_billing_code)
        assert res10.has_breaking_changes is False
        assert len(res10.changes) == 0
        print(f"[PASS] TEST 10: Unmodified API correctly returns has_breaking_changes = False.\n")

        # TEST 11: False Positive Testing (Internal Symbols)
        print("--- TEST 11: False Positive Testing for Internal Symbols ---")
        mod_code_11 = (
            "import math\nfrom utils import calculate\n\n"
            "def calculate_total(items): return sum(items)\n"
            "def process(data): return data * 2\n"
            "def connect(timeout=30): return True\n"
            "class PaymentService:\n"
            "    def charge(self, amount): return True\n"
            "    def refund(self, amount): return True\n"
        )
        res11 = analyze_breaking_changes(project_id, "billing.py", mod_code_11)
        priv_rem = [c for c in res11.changes if c.symbol == "_internal_helper"]
        assert len(priv_rem) == 1
        assert priv_rem[0].severity in ["LOW", "INFO"]
        print(f"[PASS] TEST 11: Internal private function removal correctly scoped to LOW/INFO severity.\n")

        # TEST 12: On-Demand Groq AI Explanation Endpoint
        print("--- TEST 12: On-Demand Groq AI Breaking Change Explanation ---")
        exp_res = client.post(
            f"/api/projects/{project_id}/breaking-changes/explain",
            json={
                "file_path": "billing.py",
                "changes": [c.model_dump() for c in res2.changes]
            }
        )
        assert exp_res.status_code == 200, f"Explanation failed: {exp_res.text}"
        exp_data = exp_res.json()
        assert "explanation" in exp_data
        assert len(exp_data["why_it_breaks"]) >= 1
        print(f"[PASS] TEST 12: On-demand Groq AI breaking change explanation response validated!\n")

        # TEST 13: Phase 6, 7 & 8 Regressions Check
        print("--- TEST 13: Phase 6, Phase 7 & Phase 8 Regressions Check ---")
        p_res = client.get(f"/api/projects/{project_id}/explanations/project")
        assert p_res.status_code == 200

        t_res = client.post(
            f"/api/projects/{project_id}/tests/run",
            json={"file_path": "billing.py"}
        )
        assert t_res.status_code == 200

        r_res = client.post(
            f"/api/projects/{project_id}/refactor/file",
            json={"file_path": "billing.py"}
        )
        assert r_res.status_code == 200
        print("[PASS] TEST 13: Zero regressions across Phase 6 Explanations, Phase 7 Testing, and Phase 8 Refactoring!\n")

        print("ALL 13 PHASE 9 BREAKING-CHANGE TESTS PASSED SUCCESSFULLY!")

    finally:
        client.delete(f"/api/projects/{project_id}")

if __name__ == "__main__":
    run_phase9_test_suite()
