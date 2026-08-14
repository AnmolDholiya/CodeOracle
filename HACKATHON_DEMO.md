# CodeOracle — Hackathon Demo Script (3–5 Minutes)

This document provides a concise step-by-step walkthrough script for demonstrating **CodeOracle** to judges.

---

## 🎯 Demo Goal
Demonstrate how CodeOracle turns a messy, un-tested legacy Python codebase into a modern, fully tested, refactored, and breaking-change-verified project in under 3 minutes.

---

## 🎬 Step-by-Step Demo Sequence

### Step 1: Upload Legacy Codebase (0:00 - 0:30)
1. Open `http://localhost:5173`. Point out the clean UI landing screen and system health indicator ("API Health: Groq Provider Active").
2. Drag and drop `sample_legacy.zip` (or paste a public GitHub repository URL into the **GitHub Repository URL** tab).
3. Highlight the **non-blocking background processing progress bar** (shows AST indexing stage and 350k LOC scalability).

### Step 2: Codebase Understanding & AI Explanations (0:30 - 1:15)
1. Show **Project Overview**: Click "[Generate Project Overview]". Show how Groq AI summarizes system architecture, key modules (`main.py`, `utils/math_ops.py`), and tech stack.
2. Show **File Explanation**: Select `utils/math_ops.py` and view the structured module breakdown.
3. Show **Function Explanation**: Select `calculate_discount()` to view target scope, parameters, return values, and legacy smells.

### Step 3: Test Generation & Coverage Calculation (1:15 - 2:00)
1. Click **"[Generate Unit Tests]"** for `utils/math_ops.py`. Show how Groq AI generates valid executable `pytest` code sandboxed with `ast.parse()`.
2. Click **"[Run Pytest Suite & Coverage]"**.
3. Point out the test execution output (Passed count, Duration) and **actual statement coverage percentage** calculated programmatically via `coverage.py`.

### Step 4: AI Modern Code Refactoring (2:00 - 2:45)
1. Open the **AI Modern Refactoring** card.
2. View **Local AST Code Smells**: Highlight static analysis findings (e.g. unused imports, missing error handling).
3. Click **"[Refactor File]"** (or function).
4. Show the **Unified Diff Viewer**: Switch between **Refactored Code**, **Original Code**, and **Unified Diff**.
5. Emphasize **Original Code Protection**: Original source code on disk is untouched until explicitly saved by clicking "[Save Refactored Code to Disk]".

### Step 5: Breaking-Change Detection & AI Explanation (2:45 - 3:30)
1. Open **Breaking-Change Detector**.
2. Paste or select a candidate signature shift (e.g. modifying `calculate_total(items)` to `calculate_total(items, tax)` requiring `tax`).
3. Click **"[Analyze Breaking Changes]"**.
4. Show the **instant local AST detection**:
   - `PARAMETER_ADDED` (HIGH severity)
   - `BREAKING_CALL_SITE` in `checkout.py` at line 4.
5. Click **"[Explain Breaking Changes]"** to showcase on-demand Groq AI migration guidance and backward-compatible alternatives.

---

## 🏆 Differentiating Highlights for Judges
- **Local AST Indexing Engine**: Zero source code dumps sent to AI during indexing.
- **100% Deterministic Verification**: Actual pytest runner and actual `coverage.py` statement metrics.
- **Safety First**: Original code disk protection and syntax sandboxing (`ast.parse`).
