# CodeOracle — Architecture & Design Document

## 🏗️ Architectural Overview

CodeOracle is architected with a strict separation between **fast, local static analysis** and **targeted AI LLM inference**.

```text
       ┌─────────────────────────────────────────────────────────┐
       │                 React Frontend (Vite)                   │
       └────────────────────────────┬────────────────────────────┘
                                    │ HTTP / REST APIs
       ┌────────────────────────────▼────────────────────────────┐
       │                   FastAPI Backend Server                │
       └──────┬──────────────────────┬────────────────────┬──────┘
              │                      │                    │
   ┌──────────▼──────────┐ ┌─────────▼─────────┐ ┌────────▼────────┐
   │ Workspace Manager   │ │ Local AST Visitor │ │ Pytest &       │
   │ & Security Validator│ │ & Dep. Graph      │ │ Coverage Engine│
   └──────────┬──────────┘ └─────────┬─────────┘ └────────┬───────┘
              │                      │                    │
              └──────────────────────┼────────────────────┘
                                     │ Targeted Context ONLY
                               ┌─────▼─────┐
                               │  Groq LLM │
                               └───────────┘
```

---

## ⚡ The 350,000 LOC Scalability Solution

### Problem
Large legacy codebases (10,000 to 350,000+ LOC) exceed context window limits and consume massive token budgets if raw source dumps are sent to an LLM provider.

### Solution
1. **Local AST Indexing (`python_ast.py`)**:
   When a project `.zip` is uploaded, FastAPI parses Python AST trees locally using standard `ast.walk()`. It extracts module hierarchies, classes, function signatures, decorator symbols, and call graphs without invoking external APIs.
2. **Dependency Graph Construction (`dependency_graph.py`)**:
   Imports and function invocations are categorized into **Internal Project Imports**, **External Third-Party Libraries**, and **Built-in Standard Library Modules**.
3. **Targeted Context Isolation**:
   When a user requests a file explanation, unit test generation, or code refactoring, CodeOracle isolates **only** the target file's AST definition and its immediate dependency signatures.
4. **Result**:
   350,000 LOC project indexing completes locally in seconds with **0 Groq API tokens consumed**. AI calls are made strictly on-demand for focused snippets (typically < 300 LOC).

---

## 🔒 Security & Code Protection Pipeline

1. **Workspace Path Isolation**:
   All extracted files are restricted to isolated temporary workspace directories (`d:\CodeOracle\backend\workspaces\<project_id>\`). Paths are validated using `_ensure_safe_path()` to block ZIP path traversal (`../`) attacks.
2. **Syntax Sandboxing**:
   AI-generated unit tests and refactored code pass through `ast.parse()` syntax validation before execution or diff rendering. Malformed code with invalid syntax is rejected automatically.
3. **Original Source Protection**:
   Source code on disk is **never** modified or overwritten during AI refactoring. Updates occur strictly when the user explicitly triggers `POST /refactor/save`.
4. **Environment Isolation**:
   `GROQ_API_KEY` is loaded exclusively by the FastAPI backend runtime (`backend/.env`). No secrets or API credentials are exposed to frontend client bundles.

---

## 📊 Testing & Breaking Change Detection Engines

- **Automated Pytest & Coverage Engine**:
  Runs generated unit tests in isolated subprocesses using `sys.executable -m pytest`. Programmatically invokes `coverage.py` (`coverage run` & `coverage json`) to extract exact statement coverage percentages and missing line numbers.
- **AST Breaking Change Detector**:
  Compares AST trees between original and modified code locally. Computes parameter additions/removals/renames, signature shifts, and scans call nodes across workspace files to flag breaking call sites (`BREAKING_CALL_SITE`) instantly.
