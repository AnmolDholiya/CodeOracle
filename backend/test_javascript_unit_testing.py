import os
import sys
import asyncio

# Ensure app package is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.extractor import create_empty_project_workspace
from app.services.unit_testing_service import (
    generate_unit_tests,
    run_unit_tests,
    get_test_coverage
)

async def test_js_ts_pipeline():
    print("=== Testing JavaScript & TypeScript Unit Testing Engine ===")
    
    # 1. Create temporary workspace with sample JS, TS, and package.json
    project_id, project_dir = create_empty_project_workspace("test_js_project.zip")
    print(f"Created temp workspace: {project_id} at {project_dir}")

    # Write package.json
    pkg_json = {
        "name": "js-test-sample",
        "type": "module",
        "devDependencies": {
            "vitest": "^1.0.0"
        }
    }
    with open(os.path.join(project_dir, "package.json"), "w", encoding="utf-8") as f:
        import json
        json.dump(pkg_json, f, indent=2)

    # Write sample calculator.js
    js_code = """
export function add(a, b) {
    if (typeof a !== 'number' || typeof b !== 'number') {
        throw new TypeError('Arguments must be numbers');
    }
    return a + b;
}

export function multiply(a, b) {
    return a * b;
}
"""
    with open(os.path.join(project_dir, "calculator.js"), "w", encoding="utf-8") as f:
        f.write(js_code)

    # Write sample user.ts
    ts_code = """
export interface User {
    id: number;
    name: string;
    email: string;
}

export function formatUser(user: User): string {
    return `${user.name} <${user.email}>`;
}
"""
    with open(os.path.join(project_dir, "user.ts"), "w", encoding="utf-8") as f:
        f.write(ts_code)

    # 2. Test JS Unit Test Generation
    print("\n--- Generating JS Unit Tests for calculator.js ---")
    gen_js_res = await generate_unit_tests(project_id, "calculator.js")
    print(f"Status: {gen_js_res.status}")
    print(f"Language: {gen_js_res.language}")
    print(f"Framework: {gen_js_res.framework}")
    print(f"Test file: {gen_js_res.test_file_path}")
    print(f"Code preview:\n{gen_js_res.test_code[:150]}")
    assert gen_js_res.language == "javascript"
    assert gen_js_res.framework == "vitest"
    assert os.path.exists(os.path.join(project_dir, gen_js_res.test_file_path))

    # 3. Test TS Unit Test Generation
    print("\n--- Generating TS Unit Tests for user.ts ---")
    gen_ts_res = await generate_unit_tests(project_id, "user.ts")
    print(f"Status: {gen_ts_res.status}")
    print(f"Language: {gen_ts_res.language}")
    print(f"Framework: {gen_ts_res.framework}")
    print(f"Test file: {gen_ts_res.test_file_path}")
    assert gen_ts_res.language == "typescript"
    assert os.path.exists(os.path.join(project_dir, gen_ts_res.test_file_path))

    # 4. Test JS/TS Execution
    print("\n--- Running JS/TS Unit Tests ---")
    exec_res = run_unit_tests(project_id, "calculator.js")
    print(f"Status: {exec_res.status}")
    print(f"Total: {exec_res.total}, Passed: {exec_res.passed}")
    print(f"Language: {exec_res.language}, Framework: {exec_res.framework}")
    print(f"Missing deps: {exec_res.missing_dependencies}")

    # 5. Test Coverage
    print("\n--- Checking JS/TS Coverage ---")
    cov_res = get_test_coverage(project_id, "calculator.js")
    print(f"Overall Coverage: {cov_res.overall_coverage}%")
    print(f"Language: {cov_res.language}, Framework: {cov_res.framework}")

    print("\n[SUCCESS] JS/TS Unit Testing Verification COMPLETE!")

if __name__ == "__main__":
    asyncio.run(test_js_ts_pipeline())
