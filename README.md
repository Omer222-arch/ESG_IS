# ESG Intelligence System

Multi-agent corporate portfolio and ESG intelligence platform.

## Phase 1 (Backend)
- LangGraph agent pipeline (Supervisor → SQL Analyst → ESG Compliance → Synthesis)
- FastAPI REST API
- Read-only SQLite Text-to-SQL
- Mock Chroma vector retrieval
- Human-in-the-loop interrupt on low evaluation scores

## Phase 2 (Frontend)
- React + Vite + TypeScript UI
- Integrated with `/health`, `/api/v1/analyze`, `/api/v1/resume`
- Human review workflow for interrupted analyses

## Run

### Backend
```bash
pip install -r requirements.txt
uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/analyze` | Run multi-agent analysis |
| POST | `/api/v1/resume` | Resume after human review |
