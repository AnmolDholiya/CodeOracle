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
    Category A: ('project_file', 'project', full_import_name)
    Category B: (display_name, 'standard_library' | 'third_party', full_import_name)
    Category C: (full_import_name, 'unresolved', full_import_name)
    """
    full_import = f"{module_name}.{imported_symbol}" if module_name and imported_symbol else (module_name or imported_symbol or "")
    
    if not full_import:
        return None, "unresolved", ""

    current_file_clean = current_file_rel.replace("\\", "/")

    # ----------------------------------------------------
    # Step 1: Check Relative Imports (Python & JS/TS)
    # ----------------------------------------------------
    is_relative = module_name.startswith(".") if module_name else False
    if is_relative:
        curr_dir = os.path.dirname(current_file_clean)
        parts = [p for p in curr_dir.split("/") if p]

        if module_name.startswith("../"):
            temp = module_name
            dots = 0
            while temp.startswith("../"):
                dots += 1
                temp = temp[3:]
            clean_mod = temp.lstrip("/")
            for _ in range(dots):
                if parts:
                    parts.pop()
            base_dir = "/".join(parts)
        elif module_name.startswith("./"):
            clean_mod = module_name[2:]
            base_dir = curr_dir
        else:
            # Python style .module or ..module
            dots = len(module_name) - len(module_name.lstrip("."))
            clean_mod = module_name[dots:]
            for _ in range(max(0, dots - 1)):
                if parts:
                    parts.pop()
            base_dir = "/".join(parts)

        # Extensions to check (including empty extension if import already specifies .js / .ts / .py)
        exts = ["", ".py", ".js", ".jsx", ".ts", ".tsx", "/index.js", "/index.jsx", "/index.ts", "/index.tsx"]
        candidates = []
        for ext in exts:
            if base_dir:
                candidates.append(f"{base_dir}/{clean_mod}{ext}")
            else:
                candidates.append(f"{clean_mod}{ext}")

        for cand in candidates:
            if cand in project_files_set and cand != current_file_clean:
                return cand, "project", full_import

    # ----------------------------------------------------
    # Step 2: Check Absolute Project-Local Imports
    # ----------------------------------------------------
    mod_str = module_name or ""
    sym_str = imported_symbol or ""

    candidates = []
    exts = ["", ".py", ".js", ".jsx", ".ts", ".tsx", "/index.js", "/index.jsx", "/index.ts", "/index.tsx"]
    for ext in exts:
        if mod_str and sym_str:
            candidates.append(f"{mod_str.replace('.', '/')}/{sym_str}{ext}")
        if mod_str:
            candidates.append(f"{mod_str.replace('.', '/')}{ext}")
            top_mod = mod_str.split(".")[0]
            candidates.append(f"{top_mod}{ext}")

    for cand in candidates:
        if cand in project_files_set and cand != current_file_clean:
            return cand, "project", full_import

    # ----------------------------------------------------
    # Step 3: Classify into External vs Unresolved
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
    Generates structured project dependency graph, external libraries, and unresolved imports.
    """
    # 1. Build set of project files and initial node registry
    project_files_set: Set[str] = set()
    nodes_map: Dict[str, DependencyNode] = {}

    for file_ast in ast_analysis.files_analyzed:
        rel_path = file_ast.relative_path.replace("\\", "/")
        project_files_set.add(rel_path)

        total_methods = sum(len(c.methods) for c in file_ast.classes)
        func_count = len(file_ast.functions) + total_methods

        nodes_map[rel_path] = DependencyNode(
            id=rel_path,
            label=os.path.basename(rel_path),
            type="file",
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
        source_rel = file_ast.relative_path.replace("\\", "/")
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

    # 3. Format External Libraries grouped list
    external_libraries_list: List[ExternalLibraryDetail] = []
    for (lib_name, lib_type), imp_set in sorted(external_grouped.items(), key=lambda x: x[0][0]):
        external_libraries_list.append(ExternalLibraryDetail(
            name=lib_name,
            top_module=lib_name.lower().replace(" ", "_"),
            type=lib_type,
            imports=sorted(list(imp_set))
        ))

    # 4. Construct Nodes and Edges
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
