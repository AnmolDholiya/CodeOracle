# CodeOracle — AI-Powered Legacy Codebase Explainer, Tester & Modernizer

> **Hack Orbit PS-06 Final Hackathon Project**  
> **Status**: 100% Feature-Complete & Production Ready

CodeOracle is a state-of-the-art developer platform designed to understand, test, refactor, and detect breaking API changes in legacy Python codebases.

---

## 🌟 Key Differentiating Features

1. **350,000 LOC Targeted AST Architecture**:
   Never dumps full raw source code to AI. Employs local Python AST indexing, dependency graph traversal, and targeted symbol context resolution to query Groq LLM efficiently.
2. **AI Code Explanations**:
   Generates architectural overview, module-level breakdowns, and line-by-line function explanations.
3. **On-Demand Pytest Generation & Coverage.py Calculation**:
   Generates real executable pytest suites using Groq AI + `ast.parse()` syntax validation, runs them safely in isolated subprocesses, and computes actual statement coverage percentages.
4. **AI-Powered Code Refactoring**:
   Identifies local AST code smells (excessive nesting, long functions, unused imports, complex conditionals), applies Groq AI modernizations, renders side-by-side unified diffs (`difflib`), runs pre/post pytest comparison, and enforces **Original Code Protection** (never overwrites disk without explicit user approval).
5. **AST Breaking-Change Detector & AI Explainer**:
   Performs fast, local static comparison between original and modified ASTs to detect signature mismatches (`FUNCTION_REMOVED`, `PARAMETER_ADDED`, `PARAMETER_RENAMED`, `CLASS_REMOVED`, `BROKEN_IMPORT`). Traverses workspace call nodes (`BREAKING_CALL_SITE`) and provides on-demand Groq AI migration guides.

---

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python 3.12+), Built-in `ast` module, `coverage.py`, `pytest`, `pydantic`.
- **Frontend**: React (Vite), Lucide Icons, Glassmorphism CSS design system.
- **AI Engine**: Groq Provider (`llama-3.3-70b-versatile`) with structured JSON outputs.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+
- Groq API Key (`GROQ_API_KEY`)

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env and insert your GROQ_API_KEY

python -m uvicorn app.main:app --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Access the application at `http://localhost:5173`.

---

## 🔐 Environment Variables

Create `backend/.env` (or copy `backend/.env.example`):
```env
PORT=8000
HOST=0.0.0.0
AI_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_MAX_OUTPUT_TOKENS=2048
```

> **Security Note**: Secrets are strictly isolated to `backend/.env`. No API keys are exposed to the frontend browser bundle.

---

## 📡 Core API Endpoints Reference

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| `GET`  | `/api/health` | System health check (Uptime, AI provider status) |
| `POST` | `/api/projects/upload` | Uploads legacy codebase `.zip` archive |
| `POST` | `/api/projects/upload_github` | Downloads & extracts public GitHub repository `.zip` |
| `GET`  | `/api/projects/{id}/status` | Status polling for non-blocking background indexing |
| `GET`  | `/api/projects/{id}/explanations/project` | Generates or fetches cached Project Overview |
| `POST` | `/api/projects/{id}/explanations/file` | Generates Module File explanation |
| `POST` | `/api/projects/{id}/explanations/function` | Generates Function explanation |
| `POST` | `/api/projects/{id}/tests/generate` | Generates executable pytest suite |
| `POST` | `/api/projects/{id}/tests/run` | Runs pytest suite & calculates `coverage.py` |
| `POST` | `/api/projects/{id}/refactor/file` | Refactors Python module file & computes pre/post metrics |
| `POST` | `/api/projects/{id}/refactor/save` | Saves approved refactored code to disk |
| `POST` | `/api/projects/{id}/breaking-changes/analyze` | Fast local AST breaking change detection |
| `POST` | `/api/projects/{id}/breaking-changes/explain` | On-demand Groq AI technical migration explanation |
