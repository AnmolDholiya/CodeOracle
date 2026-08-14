# CodeOracle — Production Deployment Guide

This guide covers step-by-step instructions for deploying **CodeOracle** in production:
- **Frontend**: Deployed to [Vercel](https://vercel.com) (React + Vite)
- **Backend**: Deployed to [Render](https://render.com) (FastAPI + Uvicorn)
- **AI Engine**: Groq API (`GROQ_API_KEY` stored exclusively in Backend Environment)

---

## 1. Environment Configuration

### Backend Environment Variables (`backend/.env` / Render Env)
Set these variables in your Render service dashboard:

| Variable | Description | Default / Example Value |
|---|---|---|
| `GROQ_API_KEY` | Your Groq API key | `gsk_...` |
| `GROQ_MODEL` | Default Groq model | `llama-3.3-70b-versatile` |
| `FRONTEND_URL` | Deployed Vercel frontend URL | `https://your-app.vercel.app` |
| `PORT` | Set automatically by Render | `10000` |
| `ENVIRONMENT` | Environment type | `production` |

### Frontend Environment Variables (`frontend/.env` / Vercel Env)
Set this variable in your Vercel project dashboard:

| Variable | Description | Example Value |
|---|---|---|
| `VITE_API_BASE_URL` | Deployed Render backend URL | `https://your-backend.onrender.com` |

---

## 2. Backend Deployment on Render

1. Log in to [Render Dashboard](https://dashboard.render.com/) and click **New +** -> **Web Service**.
2. Connect your CodeOracle GitHub repository.
3. Configure the Web Service settings:
   - **Name**: `codeoracle-backend`
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Under **Environment Variables**, add:
   - `GROQ_API_KEY` = `(your secret Groq key)`
   - `GROQ_MODEL` = `llama-3.3-70b-versatile`
   - `FRONTEND_URL` = `https://your-app.vercel.app`
   - `ENVIRONMENT` = `production`
5. Click **Create Web Service**.

> **Note**: Render provides a public URL e.g. `https://codeoracle-backend.onrender.com`. Copy this URL for Vercel configuration.

---

## 3. Frontend Deployment on Vercel

1. Log in to [Vercel Dashboard](https://vercel.com/dashboard) and click **Add New...** -> **Project**.
2. Import your CodeOracle repository.
3. Configure the Project settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Expand **Environment Variables** and add:
   - `VITE_API_BASE_URL` = `https://codeoracle-backend.onrender.com`
5. Click **Deploy**.

---

## 4. Local Development

To run CodeOracle locally:

### Start Backend:
```bash
cd backend
python -m venv venv
# On Windows: venv\Scripts\activate
# On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Frontend:
```bash
cd frontend
npm install
npm run dev
```

The frontend will run at `http://localhost:5173` and communicate with `http://localhost:8000`.

---

## 5. Verification Checklist

After deployment, test the full workflow:
- [x] **GET /health**: Returns `{"status": "ok"}`
- [x] **GET /api/health**: Returns backend health and uptime
- [x] **GET /api/ai/status**: Reports Groq configuration without exposing keys
- [x] **ZIP & GitHub Upload**: Workspace extraction and async processing
- [x] **Dependency Graph**: Interactive React Flow diagram with real dependency edges
- [x] **Unit Test Generation & Runner**: pytest for Python, Vitest/Jest for JS/TS
- [x] **Refactoring & Breaking Changes**: On-demand AST analysis & AI explainer
