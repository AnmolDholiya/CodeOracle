import os

BINARY_EXTENSIONS = {
    ".db", ".sqlite", ".sqlite3", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar", ".exe", ".dll", ".so", ".dylib",
    ".pyc", ".pyo", ".bin", ".dat", ".woff", ".woff2", ".ttf", ".eot"
}

KNOWN_CONFIG_FILENAMES = {
    ".gitignore", ".env", ".editorconfig", "dockerfile", "makefile", 
    "license", "readme", "procfile", "requirements.txt"
}

def get_file_type(file_path: str) -> str:
    """Detects broad file type category based on extension and filename."""
    clean_path = file_path.replace("\\", "/")
    filename = os.path.basename(clean_path).lower()
    ext = os.path.splitext(clean_path)[1].lower()

    if ext in [".py", ".pyw"]:
        return "python"
    elif ext in [".js", ".jsx"]:
        return "javascript"
    elif ext in [".ts", ".tsx"]:
        return "typescript"
    elif ext in [".md", ".markdown"]:
        return "markdown"
    elif ext == ".json":
        return "json"
    elif ext in [".html", ".htm"]:
        return "html"
    elif ext in [".css", ".scss", ".less"]:
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
