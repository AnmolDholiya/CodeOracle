import os
from typing import Set

# Comprehensive directory ignore set
IGNORED_DIRS: Set[str] = {
    "__pycache__", ".git", "node_modules", ".venv", "venv", "env",
    ".pytest_cache", ".idea", ".vscode", "dist", "build", ".next",
    "coverage", ".cache", ".mypy_cache", ".turbo", "bin", "obj",
    ".svn", ".hg", ".tox", ".eggs", "*.egg-info"
}

# Non-source / binary / media extensions to ignore during extraction and scanning
BINARY_EXTENSIONS: Set[str] = {
    # Databases & data
    ".db", ".sqlite", ".sqlite3", ".bin", ".dat", ".parquet", ".arrow",
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".bmp", ".tiff", ".tif", ".psd",
    # Videos & Audio
    ".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".webm", ".mp3", ".wav", ".ogg", ".m4a", ".aac",
    # Archives & Compressed
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz", ".tgz",
    # Executables & Binaries
    ".exe", ".dll", ".so", ".dylib", ".o", ".obj", ".a", ".lib", ".class", ".jar", ".war", ".ear",
    # Python compiled / caches
    ".pyc", ".pyo", ".pyd",
    # Fonts
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    # Documents / Spreadsheets
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
    # WebAssembly & Node native
    ".wasm", ".node"
}

KNOWN_CONFIG_FILENAMES: Set[str] = {
    ".gitignore", ".env", ".env.example", ".editorconfig", "dockerfile", "makefile", 
    "license", "readme", "procfile", "requirements.txt", "package.json", "tsconfig.json",
    "pyproject.toml", "setup.py", "setup.cfg", "cargo.toml", "go.mod"
}

SOURCE_EXTENSIONS: Set[str] = {
    ".py", ".pyw",
    ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx", ".mts", ".cts"
}

LANGUAGE_MAP = {
    ".py": "Python",
    ".pyw": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".mts": "TypeScript",
    ".cts": "TypeScript",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".json": "JSON",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".txt": "Plain Text"
}

def is_ignored_directory(dir_name: str) -> bool:
    """Checks if a directory name matches the standard ignore list."""
    clean_dir = dir_name.strip().lower()
    return clean_dir in IGNORED_DIRS or clean_dir.endswith(".egg-info")

def is_binary_extension(ext: str) -> bool:
    """Checks if a file extension is binary/media."""
    return ext.lower() in BINARY_EXTENSIONS

def should_extract_archive_entry(member_path: str) -> bool:
    """Determines whether a ZIP entry should be extracted to disk.
    
    Filters out ignored directories (node_modules, .git, .venv, etc.),
    system metadata (__MACOSX, .DS_Store), and binary/media files before disk extraction.
    """
    normalized = member_path.replace("\\", "/").strip()
    parts = [p.lower() for p in normalized.split("/") if p]
    
    if not parts:
        return False
        
    # Skip macOS metadata or Windows desktop junk
    if "__macosx" in parts or ".ds_store" in parts or "thumbs.db" in parts:
        return False
        
    # Check if any parent folder is an ignored directory
    for part in parts[:-1]:
        if is_ignored_directory(part):
            return False
            
    # If the entry itself is a directory
    if normalized.endswith("/"):
        return not is_ignored_directory(parts[-1])
        
    filename = parts[-1]
    ext = os.path.splitext(filename)[1]
    
    # Reject binary and media extensions
    if is_binary_extension(ext):
        return False
        
    return True

def should_analyze_source_file(file_path: str) -> bool:
    """Determines if a file is a supported source file for AST analysis."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in SOURCE_EXTENSIONS

def get_file_language(file_path_or_ext: str) -> str:
    """Returns the recognized programming language name."""
    ext = os.path.splitext(file_path_or_ext)[1].lower() if "." in file_path_or_ext else file_path_or_ext.lower()
    return LANGUAGE_MAP.get(ext, "Plain Text")

def get_file_type(file_path: str) -> str:
    """Detects broad file type category based on extension and filename."""
    clean_path = file_path.replace("\\", "/")
    filename = os.path.basename(clean_path).lower()
    ext = os.path.splitext(clean_path)[1].lower()

    if ext in [".py", ".pyw"]:
        return "python"
    elif ext in [".js", ".jsx", ".mjs", ".cjs"]:
        return "javascript"
    elif ext in [".ts", ".tsx", ".mts", ".cts"]:
        return "typescript"
    elif ext in [".md", ".markdown"]:
        return "markdown"
    elif ext == ".json":
        return "json"
    elif ext in [".html", ".htm"]:
        return "html"
    elif ext in [".css", ".scss", ".less", ".sass"]:
        return "css"
    elif ext in [".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml"] or filename in KNOWN_CONFIG_FILENAMES:
        return "config"
    elif ext in [".txt", ".log", ".rst"]:
        return "text"
    elif ext in BINARY_EXTENSIONS:
        return "binary"
    else:
        return "unknown"

def is_binary_file(file_path: str) -> bool:
    """Determines if a file is binary by checking extension or null bytes in content."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in BINARY_EXTENSIONS:
        return True

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return False

    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return True
    except Exception:
        pass

    return False
