from __future__ import annotations

import asyncio
import base64
import json
import os
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.engine import resume_analysis, run_analysis, run_analysis_events

APP_DIR = Path(__file__).resolve().parent
HISTORY_DB = APP_DIR / "analysis_history.sqlite3"
API_KEY = os.getenv("ESG_API_KEY", "dev-local-key")


class HistoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    thread_id TEXT PRIMARY KEY,
                    user_query TEXT NOT NULL,
                    status TEXT NOT NULL,
                    human_approved INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    async def upsert(self, thread_id: str, user_query: str, payload: dict[str, Any]) -> None:
        now = time.time()

        def _write() -> None:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT created_at FROM analysis_runs WHERE thread_id = ?",
                    (thread_id,),
                ).fetchone()
                created_at = float(row["created_at"]) if row else now
                conn.execute(
                    """
                    INSERT OR REPLACE INTO analysis_runs
                    (thread_id, user_query, status, human_approved, created_at, updated_at, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        thread_id,
                        user_query,
                        str(payload.get("status", "unknown")),
                        int(bool(payload.get("human_approved", False))),
                        created_at,
                        now,
                        json.dumps(payload, separators=(",", ":"), sort_keys=True),
                    ),
                )
                conn.commit()

        async with self._lock:
            await asyncio.to_thread(_write)

    async def list(self, limit: int = 50) -> list[dict[str, Any]]:
        def _read() -> list[dict[str, Any]]:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT thread_id, user_query, status, human_approved, created_at, updated_at
                    FROM analysis_runs
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                return [
                    {
                        "thread_id": row["thread_id"],
                        "user_query": row["user_query"],
                        "status": row["status"],
                        "human_approved": bool(row["human_approved"]),
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                    for row in rows
                ]

        return await asyncio.to_thread(_read)

    async def get(self, thread_id: str) -> dict[str, Any]:
        def _read() -> dict[str, Any] | None:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT payload_json FROM analysis_runs WHERE thread_id = ?",
                    (thread_id,),
                ).fetchone()
                return json.loads(row["payload_json"]) if row else None

        payload = await asyncio.to_thread(_read)
        if payload is None:
            raise KeyError(thread_id)
        return payload


history_store = HistoryStore(HISTORY_DB)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="Multi-Agent Corporate Portfolio & ESG Intelligence System",
    version="1.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        # Fetch the UI scripts safely from an alternative stable unpkg fallback
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    user_query: str = Field(..., min_length=1)
    live_web_context: str = Field(default="")
    thread_id: str | None = Field(default=None)


class ResumeRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    human_approved: bool = Field(default=True)


def require_api_key(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    bearer = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip()
    provided = x_api_key or bearer
    if API_KEY and provided != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _json_line(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode("utf-8")


def _pdf_bytes(title: str, payload: dict[str, Any]) -> bytes:
    text = json.dumps(payload, indent=2, sort_keys=True)
    lines = [title, "", *text.splitlines()]
    escaped_lines = [
        line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:100]
        for line in lines[:55]
    ]
    stream_parts = ["BT", "/F1 10 Tf", "50 780 Td", "14 TL"]
    for idx, line in enumerate(escaped_lines):
        if idx:
            stream_parts.append("T*")
        stream_parts.append(f"({line}) Tj")
    stream_parts.append("ET")
    stream = "\n".join(stream_parts).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{idx} 0 obj\n".encode())
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref_at = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode())
    out.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    )
    return bytes(out)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/analyze", dependencies=[Depends(require_api_key)])
async def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    thread_id = request.thread_id or str(uuid.uuid4())
    try:
        result = await run_analysis(
            user_query=request.user_query,
            thread_id=thread_id,
            live_web_context=request.live_web_context,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    result["thread_id"] = thread_id
    await history_store.upsert(thread_id, request.user_query, result)
    return result


@app.post("/api/v1/analyze/stream", dependencies=[Depends(require_api_key)])
async def analyze_stream(request: AnalyzeRequest) -> StreamingResponse:
    thread_id = request.thread_id or str(uuid.uuid4())

    async def events():
        try:
            async for event in run_analysis_events(
                user_query=request.user_query,
                thread_id=thread_id,
                live_web_context=request.live_web_context,
            ):
                if event.get("event") == "completed":
                    result = dict(event["result"])
                    result["thread_id"] = thread_id
                    await history_store.upsert(thread_id, request.user_query, result)
                    event["result"] = result
                yield _json_line(event)
        except Exception as exc:
            yield _json_line({"event": "error", "thread_id": thread_id, "detail": str(exc)})

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/api/v1/resume", dependencies=[Depends(require_api_key)])
async def resume(request: ResumeRequest) -> dict[str, Any]:
    try:
        result = await resume_analysis(
            thread_id=request.thread_id,
            human_approved=request.human_approved,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    result["thread_id"] = request.thread_id
    user_query = result.get("final_synthesis_report", {}).get("query", request.thread_id)
    await history_store.upsert(request.thread_id, str(user_query), result)
    return result


@app.get("/api/v1/history", dependencies=[Depends(require_api_key)])
async def history(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    return {"items": await history_store.list(limit)}


@app.get("/api/v1/history/{thread_id}", dependencies=[Depends(require_api_key)])
async def history_detail(thread_id: str) -> dict[str, Any]:
    try:
        return await history_store.get(thread_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.get("/api/v1/export/{thread_id}.{file_format}", dependencies=[Depends(require_api_key)])
async def export_run(thread_id: str, file_format: str) -> Response:
    try:
        payload = await history_store.get(thread_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    safe_id = "".join(ch for ch in thread_id if ch.isalnum() or ch in ("-", "_"))[:80]
    if file_format == "json":
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        return Response(
            body,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="esg-report-{safe_id}.json"'},
        )
    if file_format == "pdf":
        body = _pdf_bytes("ESG Intelligence Synthesis Report", payload)
        return Response(
            body,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="esg-report-{safe_id}.pdf"',
                "X-Report-Checksum": base64.urlsafe_b64encode(body[:24]).decode("ascii"),
            },
        )
    raise HTTPException(status_code=400, detail="Unsupported export format")
@app.get("/")
def home():
    return {"message": "Multi-Agent ESG Intelligence Workspace API is running cleanly inside Docker!"}

if __name__ == "__main__":
    import uvicorn
    # This lets the file boot itself up directly when called by Python
    uvicorn.run(app, host="0.0.0.0", port=8000)
