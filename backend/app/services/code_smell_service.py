import ast
from typing import List, Dict, Any, Optional

def analyze_code_smells(source_code: str, function_name: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Performs local Python AST static analysis to detect obvious code smells:
    - Long functions
    - Excessive nesting
    - Too many parameters
    - Poor/single-letter variable names
    - Overly complex conditions
    - Unused imports
    - Missing error handling / bare excepts
    - Unnecessary branches (redundant boolean returns)
    - Repeated literals
    """
    smells = []
    
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        # Fallback to static JS/TS code smell analysis
        return analyze_js_code_smells(source_code, function_name)

    # 1. Imports Analysis (Unused Imports)
    imported_names = set()
    used_names = set()

    class NameVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                imported_names.add(alias.asname or alias.name)
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            for alias in node.names:
                imported_names.add(alias.asname or alias.name)
            self.generic_visit(node)

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
            self.generic_visit(node)

    visitor = NameVisitor()
    visitor.visit(tree)

    unused = imported_names - used_names
    if unused:
        smells.append({
            "type": "unused_import",
            "description": f"Unused imports detected: {', '.join(sorted(unused))}",
            "severity": "low"
        })

    # 2. Function & Method Analysis
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # If function_name is specified, filter for that function
            if function_name and node.name != function_name:
                continue

            fn_name = node.name
            
            # Check length (lines of code)
            start_line = getattr(node, 'lineno', 1)
            end_line = getattr(node, 'end_lineno', start_line + len(ast.unparse(node).splitlines()))
            loc = end_line - start_line + 1
            if loc > 25:
                smells.append({
                    "type": "long_function",
                    "description": f"Function '{fn_name}' is long ({loc} lines). Consider modularization.",
                    "severity": "medium"
                })

            # Check parameters count
            num_args = len(node.args.args)
            if num_args > 4:
                smells.append({
                    "type": "too_many_parameters",
                    "description": f"Function '{fn_name}' takes {num_args} parameters (threshold: 4).",
                    "severity": "medium"
                })

            # Check Nesting Depth & Conditions & Bare Excepts & Redundant Branches
            max_depth = 0

            def calc_nesting(stmt_list, current_depth):
                nonlocal max_depth
                if current_depth > max_depth:
                    max_depth = current_depth

                for stmt in stmt_list:
                    if isinstance(stmt, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                        # Check complex condition on If
                        if isinstance(stmt, ast.If):
                            # Count boolean ops in test
                            bool_ops = [n for n in ast.walk(stmt.test) if isinstance(n, ast.BoolOp)]
                            if bool_ops:
                                op_count = sum(len(b.values) for b in bool_ops)
                                if op_count >= 3:
                                    smells.append({
                                        "type": "overly_complex_condition",
                                        "description": f"Function '{fn_name}' contains complex conditional expressions.",
                                        "severity": "medium"
                                    })
                            
                            # Check redundant boolean branch: if cond: return True else: return False
                            if (len(stmt.body) == 1 and isinstance(stmt.body[0], ast.Return) and
                                isinstance(stmt.body[0].value, ast.Constant) and
                                isinstance(stmt.body[0].value.value, bool)):
                                if (stmt.orelse and len(stmt.orelse) == 1 and 
                                    isinstance(stmt.orelse[0], ast.Return) and
                                    isinstance(stmt.orelse[0].value, ast.Constant) and
                                    isinstance(stmt.orelse[0].value.value, bool)):
                                    smells.append({
                                        "type": "unnecessary_branch",
                                        "description": f"Function '{fn_name}' has redundant boolean return branches.",
                                        "severity": "low"
                                    })

                        # Check Bare Except in Try
                        if isinstance(stmt, ast.Try):
                            for handler in stmt.handlers:
                                if handler.type is None:
                                    smells.append({
                                        "type": "missing_error_handling",
                                        "description": f"Function '{fn_name}' contains bare 'except:' clause.",
                                        "severity": "high"
                                    })

                        body_stmts = getattr(stmt, 'body', [])
                        calc_nesting(body_stmts, current_depth + 1)
                        if hasattr(stmt, 'orelse') and stmt.orelse:
                            calc_nesting(stmt.orelse, current_depth + 1)

            calc_nesting(node.body, 1)
            if max_depth > 3:
                smells.append({
                    "type": "excessive_nesting",
                    "description": f"Function '{fn_name}' has deep nesting level ({max_depth} deep).",
                    "severity": "high"
                })

            # Check variable naming
            for sub_node in ast.walk(node):
                if isinstance(sub_node, ast.Name) and isinstance(sub_node.ctx, ast.Store):
                    var_name = sub_node.id
                    if len(var_name) == 1 and var_name.lower() not in ['i', 'j', 'k', 'x', 'y', 'z', '_']:
                        smells.append({
                            "type": "poor_naming",
                            "description": f"Non-descriptive single-letter variable name '{var_name}' in '{fn_name}'.",
                            "severity": "low"
                        })
                    elif var_name.lower() in ['temp', 'data', 'val', 'obj', 'foo', 'bar']:
                        smells.append({
                            "type": "poor_naming",
                            "description": f"Generic variable name '{var_name}' in '{fn_name}'.",
                            "severity": "low"
                        })

    # Deduplicate smells
    unique_smells = []
    seen = set()
    for s in smells:
        key = (s["type"], s["description"])
        if key not in seen:
            seen.add(key)
            unique_smells.append(s)

    return unique_smells

def analyze_js_code_smells(source_code: str, function_name: Optional[str] = None) -> List[Dict[str, str]]:
    """Analyzes JavaScript and TypeScript source code for common code smells."""
    import re
    smells = []
    lines = source_code.splitlines()
    loc = len([l for l in lines if l.strip()])

    if loc > 30 and not function_name:
        smells.append({
            "type": "long_file",
            "description": f"File is long ({loc} lines). Consider breaking down into smaller modules.",
            "severity": "low"
        })

    # Check var usage
    var_matches = re.finditer(r"\bvar\s+([A-Za-z0-9_$]+)", source_code)
    var_count = len(list(var_matches))
    if var_count > 0:
        smells.append({
            "type": "suspicious_var_usage",
            "description": f"Found {var_count} 'var' declaration(s). Prefer 'const' or 'let' for block-scoped declarations.",
            "severity": "medium"
        })

    # Check function parameters count
    param_matches = re.finditer(r"(?:function\s+([A-Za-z0-9_$]*)|const\s+([A-Za-z0-9_$]+)\s*=)\s*(?:async\s*)?\(([^)]*)\)", source_code)
    for m in param_matches:
        fn_n = m.group(1) or m.group(2) or "anonymous"
        if function_name and fn_n != function_name:
            continue
        params_str = m.group(3).strip()
        if params_str:
            p_count = len([p for p in params_str.split(",") if p.strip()])
            if p_count > 4:
                smells.append({
                    "type": "too_many_parameters",
                    "description": f"Function '{fn_n}' takes {p_count} parameters (threshold: 4).",
                    "severity": "medium"
                })

    # Check nested callbacks / promise chaining
    callback_depth = len(re.findall(r"\.then\s*\(", source_code))
    if callback_depth >= 3:
        smells.append({
            "type": "excessive_callbacks",
            "description": f"Deep Promise chain detected ({callback_depth} .then calls). Consider refactoring to async/await.",
            "severity": "medium"
        })

    # Check empty catch blocks
    if re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", source_code):
        smells.append({
            "type": "empty_catch_block",
            "description": "Empty catch block detected. Silently swallowing exceptions can hide runtime bugs.",
            "severity": "high"
        })

    return smells
