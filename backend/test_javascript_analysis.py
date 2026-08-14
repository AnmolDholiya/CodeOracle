import os
import sys
import shutil
import tempfile

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.js_ts_ast import analyze_js_ts_file
from app.services.python_ast import analyze_project_workspace
from app.services.dependency_graph import generate_dependency_graph
from app.services.code_smell_service import analyze_code_smells

def run_tests():
    print("=== CODEORACLE JAVASCRIPT / TYPESCRIPT STATIC ANALYSIS TEST SUITE ===\n")

    # Create temporary directory for JS/TS files
    temp_dir = tempfile.mkdtemp(prefix="codeoracle_jstest_")

    try:
        # TEST 1: Simple JavaScript function declaration
        js_func_code = """
        function calculateTotal(a, b) {
            return a + b;
        }
        """
        f1_path = os.path.join(temp_dir, "test1.js")
        with open(f1_path, "w", encoding="utf-8") as f:
            f.write(js_func_code)
        
        ast1 = analyze_js_ts_file(f1_path, "test1.js")
        fn1_names = [fn.name for fn in ast1.functions]
        assert "calculateTotal" in fn1_names, "TEST 1 Failed: calculateTotal function declaration not detected"
        print("[PASS] TEST 1: Function declaration correctly detected.")

        # TEST 2: Arrow function
        js_arrow_code = """
        const multiply = (x, y = 1) => {
            return x * y;
        };
        """
        f2_path = os.path.join(temp_dir, "test2.js")
        with open(f2_path, "w", encoding="utf-8") as f:
            f.write(js_arrow_code)

        ast2 = analyze_js_ts_file(f2_path, "test2.js")
        fn2_names = [fn.name for fn in ast2.functions]
        assert "multiply" in fn2_names, "TEST 2 Failed: Arrow function multiply not detected"
        print("[PASS] TEST 2: Arrow function correctly detected.")

        # TEST 3: Async function
        js_async_code = """
        async function fetchData(url) {
            const res = await fetch(url);
            return await res.json();
        }
        """
        f3_path = os.path.join(temp_dir, "test3.js")
        with open(f3_path, "w", encoding="utf-8") as f:
            f.write(js_async_code)

        ast3 = analyze_js_ts_file(f3_path, "test3.js")
        async_fn = next((fn for fn in ast3.functions if fn.name == "fetchData"), None)
        assert async_fn is not None and async_fn.is_async, "TEST 3 Failed: Async function fetchData not detected or is_async is False"
        print("[PASS] TEST 3: Async function correctly detected with is_async=True.")

        # TEST 4: Class + methods
        js_class_code = """
        class UserService extends BaseService {
            constructor(api) {
                super();
                this.api = api;
            }
            async getUser(id) {
                return await this.api.get('/user/' + id);
            }
        }
        """
        f4_path = os.path.join(temp_dir, "test4.js")
        with open(f4_path, "w", encoding="utf-8") as f:
            f.write(js_class_code)

        ast4 = analyze_js_ts_file(f4_path, "test4.js")
        assert len(ast4.classes) == 1, "TEST 4 Failed: Class count mismatch"
        cls = ast4.classes[0]
        assert cls.name == "UserService", "TEST 4 Failed: Class name mismatch"
        assert "BaseService" in cls.bases, "TEST 4 Failed: Inheritance base class mismatch"
        m_names = [m.name for m in cls.methods]
        assert "getUser" in m_names, "TEST 4 Failed: Method getUser not detected"
        print("[PASS] TEST 4: Class declaration & methods correctly detected.")

        # TEST 5: ES module imports
        js_imp_code = """
        import { useState, useEffect } from "react";
        import axios from "axios";
        import UserCard from "./components/UserCard.jsx";
        """
        f5_path = os.path.join(temp_dir, "test5.js")
        with open(f5_path, "w", encoding="utf-8") as f:
            f.write(js_imp_code)

        ast5 = analyze_js_ts_file(f5_path, "test5.js")
        modules = [imp.module for imp in ast5.imports]
        assert "react" in modules and "axios" in modules and "./components/UserCard.jsx" in modules, "TEST 5 Failed: ES Module imports missing"
        print("[PASS] TEST 5: ES module imports correctly extracted.")

        # TEST 6: CommonJS require
        js_cjs_code = """
        const fs = require('fs');
        const { parse } = require('path');
        """
        f6_path = os.path.join(temp_dir, "test6.js")
        with open(f6_path, "w", encoding="utf-8") as f:
            f.write(js_cjs_code)

        ast6 = analyze_js_ts_file(f6_path, "test6.js")
        cjs_mods = [imp.module for imp in ast6.imports if imp.import_type == "commonjs"]
        assert "fs" in cjs_mods and "path" in cjs_mods, "TEST 6 Failed: CommonJS require imports missing"
        print("[PASS] TEST 6: CommonJS require() imports correctly detected.")

        # TEST 7: Exports
        js_exp_code = """
        export const API_URL = "http://localhost";
        export default function App() {}
        module.exports = { calculateTotal };
        """
        f7_path = os.path.join(temp_dir, "test7.js")
        with open(f7_path, "w", encoding="utf-8") as f:
            f.write(js_exp_code)

        ast7 = analyze_js_ts_file(f7_path, "test7.js")
        exp_names = [e.exported_name for e in ast7.exports]
        assert len(exp_names) >= 2, "TEST 7 Failed: Export count missing"
        print("[PASS] TEST 7: Exports correctly extracted.")

        # TEST 8: React JSX component
        jsx_code = """
        import React from 'react';
        export default function UserCard({ name, age }) {
            return <div>{name} - {age}</div>;
        }
        """
        f8_path = os.path.join(temp_dir, "UserCard.jsx")
        with open(f8_path, "w", encoding="utf-8") as f:
            f.write(jsx_code)

        ast8 = analyze_js_ts_file(f8_path, "UserCard.jsx")
        comp_names = [c.name for c in ast8.components]
        assert "UserCard" in comp_names, "TEST 8 Failed: React JSX Component UserCard not detected"
        print("[PASS] TEST 8: React JSX Component correctly detected.")

        # TEST 9: TypeScript interface
        ts_if_code = """
        interface UserProfile {
            id: number;
            username: string;
            email?: string;
        }
        """
        f9_path = os.path.join(temp_dir, "types.ts")
        with open(f9_path, "w", encoding="utf-8") as f:
            f.write(ts_if_code)

        ast9 = analyze_js_ts_file(f9_path, "types.ts")
        if_names = [i.name for i in ast9.interfaces]
        assert "UserProfile" in if_names, "TEST 9 Failed: TypeScript interface UserProfile not detected"
        print("[PASS] TEST 9: TypeScript interface correctly extracted.")

        # TEST 10: TypeScript type alias
        ts_type_code = """
        type UserRole = "admin" | "editor" | "viewer";
        """
        f10_path = os.path.join(temp_dir, "roleTypes.ts")
        with open(f10_path, "w", encoding="utf-8") as f:
            f.write(ts_type_code)

        ast10 = analyze_js_ts_file(f10_path, "roleTypes.ts")
        type_names = [t.name for t in ast10.types]
        assert "UserRole" in type_names, "TEST 10 Failed: TypeScript type alias UserRole not detected"
        print("[PASS] TEST 10: TypeScript type alias correctly extracted.")

        # TEST 11: Mixed Python + JavaScript + TypeScript project scan
        py_code = "def main(): print('hello')"
        with open(os.path.join(temp_dir, "app.py"), "w", encoding="utf-8") as f:
            f.write(py_code)

        proj_ast = analyze_project_workspace(temp_dir, "test_mixed_proj")
        assert proj_ast.total_python_files >= 1, "TEST 11 Failed: Python files missing in mixed project scan"
        assert proj_ast.total_javascript_files >= 1, "TEST 11 Failed: JavaScript files missing in mixed project scan"
        assert proj_ast.total_typescript_files >= 1, "TEST 11 Failed: TypeScript files missing in mixed project scan"
        print(f"[PASS] TEST 11: Mixed project scanned successfully! (Py: {proj_ast.total_python_files}, JS: {proj_ast.total_javascript_files}, TS: {proj_ast.total_typescript_files}).")

        # TEST 12: Invalid JS file parse recovery
        bad_js_path = os.path.join(temp_dir, "bad_syntax.js")
        with open(bad_js_path, "w", encoding="utf-8") as f:
            f.write("const a = ; /// BAD SYNTAX")

        ast12 = analyze_js_ts_file(bad_js_path, "bad_syntax.js")
        # Tree-sitter recovers gracefully or records error without throwing exception
        assert ast12 is not None, "TEST 12 Failed: Invalid JS file caused total crash"
        print("[PASS] TEST 12: Invalid JS file handled gracefully without crashing workspace indexing.")

        # TEST 13: Code Smells for JS
        bad_var_js = "var x = 10;\nvar y = 20;\ncatch (e) {}"
        smells = analyze_code_smells(bad_var_js)
        smell_types = [s["type"] for s in smells]
        assert "suspicious_var_usage" in smell_types or "empty_catch_block" in smell_types, "TEST 13 Failed: JS Code smells missing"
        print("[PASS] TEST 13: JavaScript static code smell scanner verified.")

        print("\nALL 13 JAVASCRIPT / TYPESCRIPT STATIC ANALYSIS TESTS PASSED SUCCESSFULLY!")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_tests()
