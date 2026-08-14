import os
import re
import time
from typing import List, Set, Tuple, Optional
from app.schemas.ast import (
    ASTFileAnalysis,
    ImportDetail,
    ExportDetail,
    ClassDetail,
    FunctionDetail,
    ParameterDetail,
    InterfaceDetail,
    TypeDetail,
    ComponentDetail
)

try:
    import tree_sitter
    import tree_sitter_javascript
    JS_LANGUAGE = tree_sitter.Language(tree_sitter_javascript.language())
    TREE_SITTER_AVAILABLE = True
except Exception as ts_err:
    TREE_SITTER_AVAILABLE = False
    JS_LANGUAGE = None

def get_language_from_ext(ext: str) -> str:
    ext_lower = ext.lower()
    if ext_lower == ".js":
        return "JavaScript"
    elif ext_lower == ".jsx":
        return "JSX"
    elif ext_lower == ".ts":
        return "TypeScript"
    elif ext_lower == ".tsx":
        return "TSX"
    return "JavaScript"

def parse_js_parameters(node, code_bytes: bytes) -> List[ParameterDetail]:
    """Extracts parameter names, annotations, and default values from JS/TS function node."""
    params: List[ParameterDetail] = []
    
    # Locate formal_parameters or parameters node
    param_node = None
    for child in node.children:
        if child.type in ("formal_parameters", "parameters"):
            param_node = child
            break
            
    if not param_node:
        return params

    for p in param_node.children:
        if p.type in (",", "(", ")", "{", "}"):
            continue
            
        p_text = p.text.decode("utf-8", errors="ignore").strip()
        p_name = p_text
        default_val = None
        annotation = None

        if p.type == "assignment_pattern":
            # e.g. tax = 0
            left = p.child_by_field_name("left")
            right = p.child_by_field_name("right")
            if left:
                p_name = left.text.decode("utf-8", errors="ignore")
            if right:
                default_val = right.text.decode("utf-8", errors="ignore")
        elif p.type == "rest_pattern" or p_text.startswith("..."):
            p_name = p_text
        elif ":" in p_text:
            parts = p_text.split(":", 1)
            p_name = parts[0].strip()
            annotation = parts[1].strip()

        if p_name:
            params.append(ParameterDetail(
                name=p_name,
                annotation=annotation,
                default=default_val
            ))

    return params

def extract_calls_from_js_node(node, code_bytes: bytes) -> Set[str]:
    """Traverses AST node to collect function/method calls."""
    calls: Set[str] = set()

    def walk(n):
        if n.type == "call_expression":
            fn_child = n.child_by_field_name("function")
            if fn_child:
                fn_text = fn_child.text.decode("utf-8", errors="ignore").strip()
                if fn_text and fn_text != "require":
                    calls.add(fn_text)
        for child in n.children:
            walk(child)

    walk(node)
    return calls

def analyze_js_ts_file(file_path: str, relative_path: str) -> ASTFileAnalysis:
    """Parses a JavaScript or TypeScript source file into structured AST analysis metadata."""
    ext = os.path.splitext(file_path)[1]
    lang = get_language_from_ext(ext)
    
    lines_of_code = 0
    content = ""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines_of_code = len([l for l in content.splitlines() if l.strip()])
    except Exception as read_err:
        return ASTFileAnalysis(
            relative_path=relative_path,
            absolute_path=file_path,
            lines_of_code=0,
            language=lang,
            has_syntax_error=True,
            syntax_error_message=f"Failed to read file: {str(read_err)}"
        )

    if not content.strip():
        return ASTFileAnalysis(
            relative_path=relative_path,
            absolute_path=file_path,
            lines_of_code=0,
            language=lang
        )

    code_bytes = content.encode("utf-8")
    
    imports: List[ImportDetail] = []
    exports: List[ExportDetail] = []
    classes: List[ClassDetail] = []
    functions: List[FunctionDetail] = []
    global_calls_set: Set[str] = set()
    interfaces: List[InterfaceDetail] = []
    types: List[TypeDetail] = []
    components: List[ComponentDetail] = []

    # Tree-Sitter AST Parsing
    if TREE_SITTER_AVAILABLE and JS_LANGUAGE:
        try:
            parser = tree_sitter.Parser(JS_LANGUAGE)
            tree = parser.parse(code_bytes)
            root = tree.root_node

            def traverse_top_level(n):
                node_type = n.type
                line_no = n.start_point[0] + 1
                end_line_no = n.end_point[0] + 1

                # 1. ES6 Imports
                if node_type == "import_statement":
                    mod_path = None
                    imp_source = n.child_by_field_name("source")
                    if imp_source:
                        mod_path = imp_source.text.decode("utf-8", errors="ignore").strip("\"'")
                    
                    imp_clause = n.child_by_field_name("import_clause")
                    if imp_clause:
                        clause_text = imp_clause.text.decode("utf-8", errors="ignore")
                        imports.append(ImportDetail(
                            module=mod_path,
                            name=clause_text,
                            line_number=line_no,
                            import_type="es_module"
                        ))
                    else:
                        imports.append(ImportDetail(
                            module=mod_path,
                            line_number=line_no,
                            import_type="es_module"
                        ))

                # 2. ES6 Exports
                elif node_type == "export_statement":
                    exp_text = n.text.decode("utf-8", errors="ignore").strip()
                    is_def = "default" in exp_text
                    
                    declaration = n.child_by_field_name("declaration")
                    exp_name = "default" if is_def else "named_export"
                    if declaration:
                        if declaration.type == "function_declaration":
                            fn_id = declaration.child_by_field_name("name")
                            if fn_id:
                                exp_name = fn_id.text.decode("utf-8", errors="ignore")
                        elif declaration.type in ("lexical_declaration", "variable_declaration"):
                            # export const foo = ...
                            var_text = declaration.text.decode("utf-8", errors="ignore")
                            match = re.search(r"(?:const|let|var)\s+([A-Za-z0-9_$]+)", var_text)
                            if match:
                                exp_name = match.group(1)
                                
                    exports.append(ExportDetail(
                        exported_name=exp_name,
                        is_default=is_def,
                        export_type="default" if is_def else "named",
                        line_number=line_no
                    ))

                    # Traverse declaration inside export
                    if declaration:
                        traverse_top_level(declaration)

                # 3. Functions (Declarations)
                elif node_type == "function_declaration":
                    fn_name_node = n.child_by_field_name("name")
                    fn_name = fn_name_node.text.decode("utf-8", errors="ignore") if fn_name_node else "anonymous"
                    params = parse_js_parameters(n, code_bytes)
                    is_async = "async" in n.text.decode("utf-8", errors="ignore")[:30]
                    calls = sorted(list(extract_calls_from_js_node(n, code_bytes)))

                    functions.append(FunctionDetail(
                        name=fn_name,
                        parameters=params,
                        calls=calls,
                        start_line=line_no,
                        end_line=end_line_no,
                        lines_of_code=(end_line_no - line_no + 1),
                        is_async=is_async
                    ))

                    # Check React Component (Starts with Uppercase and returns JSX or contains JSX)
                    if fn_name[0].isupper() if fn_name else False:
                        prop_names = [p.name for p in params]
                        components.append(ComponentDetail(
                            name=fn_name,
                            props=prop_names,
                            line_number=line_no
                        ))

                # 4. Const/Let Variable Arrow Functions / Component Declarations
                elif node_type in ("lexical_declaration", "variable_declaration"):
                    decl_text = n.text.decode("utf-8", errors="ignore")
                    # Check CommonJS require (e.g. const x = require('mod'))
                    req_match = re.search(r"(?:const|let|var)\s+(?:\{([^}]+)\}|([A-Za-z0-9_$]+))\s*=\s*require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", decl_text)
                    if req_match:
                        imported_sym = req_match.group(1) or req_match.group(2)
                        mod_src = req_match.group(3)
                        imports.append(ImportDetail(
                            module=mod_src,
                            name=imported_sym,
                            line_number=line_no,
                            import_type="commonjs"
                        ))

                    # Check Arrow function (e.g. const calculate = (a, b) => {})
                    arrow_match = re.search(r"(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(async\s*)?\(([^)]*)\)\s*=>", decl_text)
                    if arrow_match:
                        fn_name = arrow_match.group(1)
                        is_async = bool(arrow_match.group(2))
                        raw_params = arrow_match.group(3).strip()
                        param_list = [ParameterDetail(name=p.strip().split("=")[0].strip()) for p in raw_params.split(",") if p.strip()] if raw_params else []
                        calls = sorted(list(extract_calls_from_js_node(n, code_bytes)))

                        functions.append(FunctionDetail(
                            name=fn_name,
                            parameters=param_list,
                            calls=calls,
                            start_line=line_no,
                            end_line=end_line_no,
                            lines_of_code=(end_line_no - line_no + 1),
                            is_async=is_async
                        ))

                        if fn_name[0].isupper():
                            components.append(ComponentDetail(
                                name=fn_name,
                                props=[p.name for p in param_list],
                                line_number=line_no
                            ))

                # 5. Classes
                elif node_type == "class_declaration":
                    cls_name_node = n.child_by_field_name("name")
                    cls_name = cls_name_node.text.decode("utf-8", errors="ignore") if cls_name_node else "AnonymousClass"
                    
                    bases = []
                    heritage = next((c for c in n.children if c.type == "class_heritage"), None)
                    if heritage:
                        bases.append(heritage.text.decode("utf-8", errors="ignore").replace("extends", "").strip())

                    methods: List[FunctionDetail] = []
                    body_node = n.child_by_field_name("body")
                    if body_node:
                        for m in body_node.children:
                            if m.type == "method_definition":
                                m_name_node = m.child_by_field_name("name")
                                m_name = m_name_node.text.decode("utf-8", errors="ignore") if m_name_node else "anonymous"
                                m_params = parse_js_parameters(m, code_bytes)
                                m_start = m.start_point[0] + 1
                                m_end = m.end_point[0] + 1
                                m_calls = sorted(list(extract_calls_from_js_node(m, code_bytes)))
                                m_async = "async" in m.text.decode("utf-8", errors="ignore")[:20]

                                methods.append(FunctionDetail(
                                    name=m_name,
                                    parameters=m_params,
                                    calls=m_calls,
                                    start_line=m_start,
                                    end_line=m_end,
                                    lines_of_code=(m_end - m_start + 1),
                                    is_async=m_async
                                ))

                    classes.append(ClassDetail(
                        name=cls_name,
                        bases=bases,
                        start_line=line_no,
                        end_line=end_line_no,
                        methods=methods
                    ))

            for child in root.children:
                traverse_top_level(child)

        except Exception as parse_err:
            return ASTFileAnalysis(
                relative_path=relative_path,
                absolute_path=file_path,
                lines_of_code=lines_of_code,
                language=lang,
                has_syntax_error=True,
                syntax_error_message=f"Tree-sitter parse error: {str(parse_err)}"
            )

    # Fallback / Supplemental Regex Parsing for ES6 Imports, CommonJS Requires, and Dynamic Imports
    # This guarantees import extraction even if tree-sitter is not installed in the environment
    existing_modules = {imp.module for imp in imports if imp.module}

    # 1. ES6 import statements: e.g. import x from './y', import { a } from './y', import './y'
    es6_import_regex = re.compile(
        r"import\s+(?:type\s+)?(?:(?:\{[^}]*\}|[\w$]+|\*\s+as\s+[\w$]+)(?:\s*,\s*(?:\{[^}]*\}|[\w$]+|\*\s+as\s+[\w$]+))?\s+from\s+)?['\"]([^'\"]+)['\"]",
        re.MULTILINE
    )
    for m in es6_import_regex.finditer(content):
        mod_src = m.group(1)
        if mod_src and mod_src not in existing_modules:
            existing_modules.add(mod_src)
            line_num = content[:m.start()].count("\n") + 1
            imports.append(ImportDetail(
                module=mod_src,
                line_number=line_num,
                import_type="es_module"
            ))

    # 2. CommonJS require: e.g. const x = require('./y')
    require_regex = re.compile(
        r"(?:const|let|var)\s+(?:\{[^}]*\}|[\w$]+)\s*=\s*require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
        re.MULTILINE
    )
    for m in require_regex.finditer(content):
        mod_src = m.group(1)
        if mod_src and mod_src not in existing_modules:
            existing_modules.add(mod_src)
            line_num = content[:m.start()].count("\n") + 1
            imports.append(ImportDetail(
                module=mod_src,
                line_number=line_num,
                import_type="commonjs"
            ))

    # 3. Dynamic import: e.g. import('./y')
    dynamic_import_regex = re.compile(
        r"import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
        re.MULTILINE
    )
    for m in dynamic_import_regex.finditer(content):
        mod_src = m.group(1)
        if mod_src and mod_src not in existing_modules:
            existing_modules.add(mod_src)
            line_num = content[:m.start()].count("\n") + 1
            imports.append(ImportDetail(
                module=mod_src,
                line_number=line_num,
                import_type="dynamic"
            ))

    # TypeScript Interface & Type Extraction via Regex (for .ts and .tsx files)
    if ext.lower() in (".ts", ".tsx"):
        # Interface matching
        interface_matches = re.finditer(r"interface\s+([A-Za-z0-9_$]+)\s*\{([^}]*)\}", content)
        for m in interface_matches:
            if_name = m.group(1)
            props_body = m.group(2)
            prop_lines = [p.strip().split(":")[0].strip() for p in props_body.split(";") if p.strip()]
            line_num = content[:m.start()].count("\n") + 1
            interfaces.append(InterfaceDetail(
                name=if_name,
                properties=prop_lines,
                line_number=line_num
            ))

        # Type alias matching
        type_matches = re.finditer(r"type\s+([A-Za-z0-9_$]+)\s*=\s*([^;]+);", content)
        for m in type_matches:
            t_name = m.group(1)
            t_def = m.group(2).strip()
            line_num = content[:m.start()].count("\n") + 1
            types.append(TypeDetail(
                name=t_name,
                definition=t_def,
                line_number=line_num
            ))

    # CommonJS module.exports / exports.foo detection
    for m in re.finditer(r"(?:module\.exports\s*=\s*([A-Za-z0-9_$]+)|exports\.([A-Za-z0-9_$]+)\s*=)", content):
        exp_sym = m.group(1) or m.group(2)
        line_num = content[:m.start()].count("\n") + 1
        if exp_sym:
            exports.append(ExportDetail(
                exported_name=exp_sym,
                is_default=bool(m.group(1)),
                export_type="commonjs",
                line_number=line_num
            ))

    return ASTFileAnalysis(
        relative_path=relative_path,
        absolute_path=file_path,
        lines_of_code=lines_of_code,
        language=lang,
        has_syntax_error=False,
        syntax_error_message=None,
        imports=imports,
        exports=exports,
        classes=classes,
        functions=functions,
        global_calls=sorted(list(global_calls_set)),
        interfaces=interfaces,
        types=types,
        components=components
    )
