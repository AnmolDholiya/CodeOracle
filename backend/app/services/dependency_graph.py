import os
import sys
import time
from typing import Dict, List, Set, Tuple, Optional
from app.schemas.ast import ProjectAnalysisResponse
from app.schemas.dependency import (
    DependencyGraphResponse,
    DependencyNode,
    DependencyEdge,
    ExternalLibraryDetail
)

# Standard library module names in Python
STDLIB_MODULE_NAMES: Set[str] = set(getattr(sys, "stdlib_module_names", {
    "os", "sys", "math", "time", "json", "ast", "re", "shutil", "tempfile",
    "uuid", "typing", "collections", "datetime", "functools", "itertools",
    "pathlib", "random", "logging", "asyncio", "unittest", "subprocess",
    "io", "zipfile", "copy", "hashlib", "base64", "socket", "http", "urllib",
    "inspect", "typing_extensions", "enum", "dataclasses", "platform", "signal",
    "select", "multiprocessing", "threading", "queue", "csv", "xml", "html",
    "email", "mimetypes", "wsgiref", "concurrent", "contextlib", "traceback"
}))

# Third-party package mapping for human-friendly library grouping
THIRD_PARTY_PACKAGE_MAP: Dict[str, str] = {
    "django": "Django",
    "rest_framework": "Django REST Framework",
    "PIL": "Pillow",
    "docx": "python-docx",
    "fitz": "PyMuPDF",
    "requests": "Requests",
    "numpy": "NumPy",
    "pandas": "Pandas",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "pydantic": "Pydantic",
    "bs4": "BeautifulSoup4",
    "cv2": "OpenCV",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "sqlalchemy": "SQLAlchemy",
    "celery": "Celery",
    "redis": "Redis",
    "yaml": "PyYAML",
    "pytest": "PyTest",
    "scipy": "SciPy",
    "sklearn": "Scikit-Learn",
    "matplotlib": "Matplotlib",
    "seaborn": "Seaborn",
    "jinja2": "Jinja2",
    "werkzeug": "Werkzeug",
    "aiohttp": "aiohttp",
    "httpx": "HTTPX",
    "starlette": "Starlette",
    "boto3": "Boto3",
    "botocore": "Botocore",
    "jwt": "PyJWT",
    "cryptography": "Cryptography",
    "passlib": "Passlib",
    "dotenv": "python-dotenv",
    "uvicorn": "Uvicorn",
    "gunicorn": "Gunicorn",
    "psycopg2": "Psycopg2",
    "pymongo": "PyMongo",
    "alembic": "Alembic"
}

# Recognized PyPI packages set for third-party classification
KNOWN_THIRD_PARTY_PACKAGES: Set[str] = {
    "django", "rest_framework", "PIL", "docx", "fitz", "requests", "numpy", "pandas",
    "flask", "fastapi", "pydantic", "bs4", "cv2", "torch", "tensorflow", "sqlalchemy",
    "celery", "redis", "yaml", "pytest", "scipy", "sklearn", "matplotlib", "seaborn",
    "jinja2", "werkzeug", "aiohttp", "httpx", "starlette", "boto3", "botocore", "jwt",
    "cryptography", "passlib", "dotenv", "uvicorn", "gunicorn", "psycopg2", "pymongo",
    "alembic", "click", "rich", "typer", "tqdm", "joblib", "plotly", "dash", "paramiko",
    "fabric", "twisted", "tornado", "gevent", "kombu", "amqp", "pika", "kafka",
    "elasticsearch", "boto", "azure", "google", "git", "github", "gitlab", "brotli"
}

# Recognized npm third-party package mappings
NPM_PACKAGE_MAP: Dict[str, str] = {
    "react": "React",
    "react-dom": "React DOM",
    "axios": "Axios",
    "express": "Express",
    "lodash": "Lodash",
    "vue": "Vue.js",
    "redux": "Redux",
    "next": "Next.js",
    "vite": "Vite",
    "tailwindcss": "TailwindCSS",
    "typescript": "TypeScript",
    "jest": "Jest",
    "cypress": "Cypress",
    "rxjs": "RxJS"
}

NODE_STDLIB: Set[str] = {
    "fs", "path", "http", "https", "events", "crypto", "util", "stream", "buffer", "url", "os", "child_process"
}

def resolve_and_classify_import(
    module_name: Optional[str],
    imported_symbol: Optional[str],
    current_file_rel: str,
    project_files_set: Set[str]
) -> Tuple[Optional[str], str, str]:
    """
    Classifies a Python or JS/TS import into:
    Category A: (target_rel_path, 'project', full_import_name)
    Category B: (display_name, 'standard_library' | 'third_party', full_import_name)
    Category C: (full_import_name, 'unresolved', full_import_name)
    """
    full_import = f"{module_name}.{imported_symbol}" if module_name and imported_symbol else (module_name or imported_symbol or "")
    
    if not full_import:
        return None, "unresolved", ""

    current_file_clean = current_file_rel.replace("\\", "/").strip("/")
    curr_dir = os.path.dirname(current_file_clean)
    case_map = {p.lower(): p for p in project_files_set}

    def match_candidate(cand_path: str) -> Optional[str]:
        clean = cand_path.replace("\\", "/").strip("/")
        while "//" in clean:
            clean = clean.replace("//", "/")
        if clean in project_files_set and clean != current_file_clean:
            return clean
        if clean.lower() in case_map and case_map[clean.lower()] != current_file_clean:
            return case_map[clean.lower()]
        return None

    exts = ["", ".py", ".pyw", ".js", ".jsx", ".ts", ".tsx", "/__init__.py", "/index.js", "/index.jsx", "/index.ts", "/index.tsx"]
    raw_candidates: List[str] = []

    mod_str = module_name or ""
    sym_str = imported_symbol or ""

    # ----------------------------------------------------
    # Step 1: Relative dot imports (Python & JS/TS)
    # ----------------------------------------------------
    if mod_str.startswith("."):
        parts = [p for p in curr_dir.split("/") if p]
        temp = mod_str
        while temp.startswith("../"):
            if parts:
                parts.pop()
            temp = temp[3:]
        if temp.startswith("./"):
            temp = temp[2:]
        elif temp.startswith("."):
            dots = len(temp) - len(temp.lstrip("."))
            for _ in range(max(0, dots - 1)):
                if parts:
                    parts.pop()
            temp = temp[dots:]

        clean_mod = temp.replace(".", "/").lstrip("/")
        base_dir = "/".join(parts)

        if clean_mod:
            raw_candidates.append(f"{base_dir}/{clean_mod}" if base_dir else clean_mod)
            if sym_str:
                raw_candidates.append(f"{base_dir}/{clean_mod}/{sym_str}" if base_dir else f"{clean_mod}/{sym_str}")
        elif sym_str:
            raw_candidates.append(f"{base_dir}/{sym_str}" if base_dir else sym_str)

    # ----------------------------------------------------
    # Step 2: Absolute / Bare Project-Local Imports
    # ----------------------------------------------------
    else:
        mod_path = mod_str.replace(".", "/")

        # A. Sibling in same directory
        if curr_dir:
            if mod_path:
                raw_candidates.append(f"{curr_dir}/{mod_path}")
                if sym_str:
                    raw_candidates.append(f"{curr_dir}/{mod_path}/{sym_str}")
            elif sym_str:
                raw_candidates.append(f"{curr_dir}/{sym_str}")

        # B. Ancestor directories (parent, grandparent, etc.)
        ancestor_parts = [p for p in curr_dir.split("/") if p]
        while ancestor_parts:
            ancestor_parts.pop()
            p_dir = "/".join(ancestor_parts)
            if p_dir and mod_path:
                raw_candidates.append(f"{p_dir}/{mod_path}")
                if sym_str:
                    raw_candidates.append(f"{p_dir}/{mod_path}/{sym_str}")

        # C. Workspace Root absolute path
        if mod_path:
            raw_candidates.append(mod_path)
            if sym_str:
                raw_candidates.append(f"{mod_path}/{sym_str}")

        # D. Project-wide suffix matching (handles root folder wrappers like CONVERSTION/...)
        if mod_path:
            for pf in project_files_set:
                for ext in (".py", ".js", ".ts", ".jsx", ".tsx"):
                    if pf.endswith(f"/{mod_path}{ext}") or pf.endswith(f"/{mod_path}/{sym_str}{ext}"):
                        raw_candidates.append(pf)

    # Check candidates for a valid project file match
    for cand in raw_candidates:
        for ext in exts:
            matched = match_candidate(f"{cand}{ext}")
            if matched:
                return matched, "project", full_import

    # ----------------------------------------------------
    # Step 3: Classify into External Library vs Unresolved
    # ----------------------------------------------------
    top_pkg = (module_name or imported_symbol or "").lstrip("./").split("/")[0].split(".")[0]

    # Category B1: Python or Node Standard Library
    if top_pkg in STDLIB_MODULE_NAMES or top_pkg in NODE_STDLIB:
        return "Standard Library", "standard_library", full_import

    # Category B2: Known Third-Party Library (Python & JS npm)
    if top_pkg in THIRD_PARTY_PACKAGE_MAP:
        return THIRD_PARTY_PACKAGE_MAP[top_pkg], "third_party", full_import
    if top_pkg in NPM_PACKAGE_MAP:
        return NPM_PACKAGE_MAP[top_pkg], "third_party", full_import

    if top_pkg in KNOWN_THIRD_PARTY_PACKAGES:
        return top_pkg, "third_party", full_import

    # Category C: Unresolved Import
    return full_import, "unresolved", full_import


def generate_dependency_graph(ast_analysis: ProjectAnalysisResponse) -> DependencyGraphResponse:
    """
    Generates structured project dependency graph, external libraries, node classifications, and edges.
    """
    # 1. Build set of project files and initial node registry
    project_files_set: Set[str] = set()
    nodes_map: Dict[str, DependencyNode] = {}

    for file_ast in ast_analysis.files_analyzed:
        rel_path = file_ast.relative_path.replace("\\", "/").strip("/")
        project_files_set.add(rel_path)

        total_methods = sum(len(c.methods) for c in file_ast.classes)
        func_count = len(file_ast.functions) + total_methods

        nodes_map[rel_path] = DependencyNode(
            id=rel_path,
            label=os.path.basename(rel_path),
            type="module",  # Will be classified based on in-degree / out-degree
            relative_path=rel_path,
            lines_of_code=file_ast.lines_of_code,
            classes_count=len(file_ast.classes),
            functions_count=func_count,
            has_syntax_error=file_ast.has_syntax_error,
            project_dependencies=[],
            external_libraries=[],
            unresolved_imports=[]
        )

    edges_set: Set[Tuple[str, str]] = set()
    
    # Map for grouping external libraries: (display_name, lib_type) -> Set of import strings
    external_grouped: Dict[Tuple[str, str], Set[str]] = {}
    unresolved_set: Set[str] = set()
    legacy_external_imports: Set[str] = set()

    # 2. Process each file's imports
    for file_ast in ast_analysis.files_analyzed:
        source_rel = file_ast.relative_path.replace("\\", "/").strip("/")
        node = nodes_map[source_rel]

        node_proj_deps = set()
        node_ext_deps = set()
        node_unres_deps = set()

        for imp in file_ast.imports:
            resolved_target, category, full_imp = resolve_and_classify_import(
                module_name=imp.module,
                imported_symbol=imp.name,
                current_file_rel=source_rel,
                project_files_set=project_files_set
            )

            if category == "project" and resolved_target:
                edges_set.add((source_rel, resolved_target))
                node_proj_deps.add(resolved_target)
            elif category in ("third_party", "standard_library"):
                lib_name = resolved_target or "External Library"
                key = (lib_name, category)
                if key not in external_grouped:
                    external_grouped[key] = set()
                if full_imp:
                    external_grouped[key].add(full_imp)
                
                node_ext_deps.add(lib_name)
                legacy_external_imports.add(full_imp or lib_name)
            elif category == "unresolved":
                if full_imp:
                    unresolved_set.add(full_imp)
                    node_unres_deps.add(full_imp)

        # Update per-node classification lists for frontend inspector
        node.project_dependencies = sorted(list(node_proj_deps))
        node.external_libraries = sorted(list(node_ext_deps))
        node.unresolved_imports = sorted(list(node_unres_deps))

    # 3. Classify node categories based on in-degree and out-degree
    in_degree: Dict[str, int] = {nid: 0 for nid in nodes_map}
    out_degree: Dict[str, int] = {nid: len(n.project_dependencies) for nid, n in nodes_map.items()}

    for src, tgt in edges_set:
        if tgt in in_degree:
            in_degree[tgt] += 1

    for nid, node in nodes_map.items():
        in_deg = in_degree[nid]
        out_deg = out_degree[nid]
        base_name = os.path.basename(node.relative_path).lower()
        name_no_ext = os.path.splitext(base_name)[0]

        if in_deg == 0 and out_deg > 0:
            # Root Entry Point (not imported by any other project file, imports other files)
            node.type = "root"
        elif in_deg > 0 and out_deg == 0:
            # Utility / Helper (imported by other project files, imports no local files)
            node.type = "utility"
        elif in_deg > 0 and out_deg > 0:
            # Intermediate core module
            node.type = "module"
        else:
            # Isolated file (in_deg == 0 and out_deg == 0)
            if any(k in name_no_ext for k in ("main", "app", "index", "server", "run", "cli", "manage", "entry")):
                node.type = "root"
            elif any(k in name_no_ext for k in ("util", "helper", "const", "type", "config", "tool", "math")):
                node.type = "utility"
            else:
                node.type = "module"

    # 4. Format External Libraries grouped list
    external_libraries_list: List[ExternalLibraryDetail] = []
    for (lib_name, lib_type), imp_set in sorted(external_grouped.items(), key=lambda x: x[0][0]):
        external_libraries_list.append(ExternalLibraryDetail(
            name=lib_name,
            top_module=lib_name.lower().replace(" ", "_"),
            type=lib_type,
            imports=sorted(list(imp_set))
        ))

    # 5. Construct Nodes and Edges
    nodes_list = list(nodes_map.values())
    edges_list = [
        DependencyEdge(
            id=f"{src}->{tgt}",
            source=src,
            target=tgt,
            relationship="imports"
        )
        for src, tgt in sorted(list(edges_set))
    ]

    # Debug logging for verification
    print(f"[Dependency Graph Debug] Generated {len(nodes_list)} nodes and {len(edges_list)} edges:")
    for n in nodes_list:
        print(f"  - Node id='{n.id}', type='{n.type}', out_deps={len(n.project_dependencies)}")
    for e in edges_list:
        print(f"  -> Edge: '{e.source}' -> '{e.target}'")

    return DependencyGraphResponse(
        project_id=ast_analysis.project_id,
        total_nodes=len(nodes_list),
        total_edges=len(edges_list),
        nodes=nodes_list,
        edges=edges_list,
        external_libraries=external_libraries_list,
        unresolved_imports=sorted(list(unresolved_set)),
        external_imports=sorted(list(legacy_external_imports)),
        created_at=time.strftime("%Y-%m-%d %H:%M:%S")
    )
