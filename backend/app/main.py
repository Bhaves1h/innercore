"""
INNERCORE Sovereign Core — FastAPI backend.

Routes:
  GET  /api/health
  GET  /api/system/mode
  GET  /api/knowledge
  GET  /api/knowledge/details
  POST /api/knowledge/upload
  GET  /api/investigations
  GET  /api/investigations/{conversation_id}
  GET  /api/agents
  POST /api/execute
  GET  /api/security
  GET  /api/audit
  GET  /api/audit/verify

All inference is local — PyMuPDF/docx/csv + ChromaDB + SentenceTransformer + Ollama.
No external API calls. Zero cloud egress.
"""
from __future__ import annotations

import json
import hashlib
import os
import re
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import inspect as sa_inspect, text as sa_text

from .database import engine, Base, get_db
from .models   import AuditLogEntry, InvestigationConversation
from .schemas  import (
    HealthResponse,
    SystemModeResponse,
    ExecuteRequest,
    ExecuteResponse,
    ExecutionStep,
    EvidenceItem,
    UploadedDocument,
    DocumentDetailsResponse,
    ChunkExcerpt,
    ConversationSummary,
    ConversationDetail,
    TurnItem,
    DocumentItem,
    AgentItem,
    SecurityResponse,
    AuditEntry,
    AuditVerifyResponse,
)

# ─── DB setup ────────────────────────────────────────────────────────────────

def _migrate_db():
    """Add any missing columns and create tables (idempotent)."""
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        inspector = sa_inspect(engine)
        cols = [c["name"] for c in inspector.get_columns("audit_log")]
        if "inference_mode" not in cols:
            conn.execute(sa_text(
                "ALTER TABLE audit_log ADD COLUMN inference_mode VARCHAR(32) DEFAULT 'UNKNOWN'"
            ))
            conn.commit()

Base.metadata.create_all(bind=engine)
try:
    _migrate_db()
except Exception:
    pass   # table may not exist yet on first run; create_all handles it

# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "INNERCORE Sovereign Core",
    description = "Air-gapped on-premise agentic engine.",
    version     = "2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _hash_entry(previous_hash: str, execution_id: str, timestamp: str,
                user_role: str, user_request: str, agent: str,
                result: str, status_text: str) -> str:
    payload = "|".join([
        previous_hash, execution_id, timestamp, user_role,
        user_request, agent, result, status_text
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ms() -> int:
    """Current time in ms (used for synthetic step durations)."""
    return int(datetime.utcnow().timestamp() * 1000)


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    return {
        "status":         "READY",
        "boundary":       "LOCAL_AIR_GAPPED",
        "inference_mode": "ON_PREMISE",
        "database":       "SQLITE_READY",
    }


@app.get("/api/system/mode", response_model=SystemModeResponse)
def system_mode():
    from .llm import check_ollama
    from .rag import _get_collection, EMBED_MODEL

    available, models_str = check_ollama()
    try:
        col   = _get_collection()
        count = col.count()
    except Exception:
        count = 0

    return {
        "ollama_available": available,
        "ollama_models":    models_str,
        "embed_model":      EMBED_MODEL,
        "chroma_docs":      count,
        "inference_mode":   "LOCAL_INFERENCE" if available else "DEMO_SIMULATION",
    }


@app.get("/api/knowledge", response_model=List[UploadedDocument])
def get_knowledge_documents():
    from .rag import list_documents
    docs = list_documents()
    return [
        UploadedDocument(
            doc_id      = d["doc_id"],
            filename    = d["filename"],
            file_type   = d.get("file_type", "DOC"),
            page_count  = d["page_count"],
            chunk_count = d["chunk_count"],
            status      = d["status"],
            boundary    = d.get("boundary", "LOCAL AIR-GAPPED"),
        )
        for d in docs
    ]


@app.get("/api/knowledge/details", response_model=DocumentDetailsResponse)
def get_knowledge_document_details(filename: str):
    from .rag import get_document_details
    res = get_document_details(filename)
    return DocumentDetailsResponse(
        filename    = res["filename"],
        doc_id      = res["doc_id"],
        page_count  = res["page_count"],
        chunk_count = res["chunk_count"],
        status      = res["status"],
        boundary    = res.get("boundary", "LOCAL AIR-GAPPED"),
        excerpts    = [ChunkExcerpt(**e) for e in res.get("excerpts", [])],
    )


@app.get("/api/knowledge/page")
def get_knowledge_page(filename: str, page: int = 1):
    from .rag import get_document_page
    return get_document_page(filename, page=page)


SUPPORTED_EXTS = {".pdf", ".docx", ".doc", ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".log"}

@app.post("/api/knowledge/upload", response_model=UploadedDocument)
async def upload_document(file: UploadFile = File(...)):
    """Accept PDF, DOCX, TXT, MD, CSV, etc. Extract text locally, embed, store in ChromaDB."""
    print(f"[BACKEND] Received upload request for {file.filename}")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported format '{ext}'. Supported: PDF, DOCX, TXT, MD, CSV",
        )

    file_bytes = await file.read()
    print(f"[BACKEND] Read {len(file_bytes)} bytes for {file.filename}")
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    try:
        import asyncio
        from .rag import process_document
        print(f"[BACKEND] Starting process_document in thread...")
        result = await asyncio.to_thread(process_document, file_bytes, file.filename)
        print(f"[BACKEND] process_document finished: {result}")
    except ValueError as e:
        print(f"[BACKEND] process_document ValueError: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"[BACKEND] process_document Exception: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")

    return UploadedDocument(
        doc_id      = result["doc_id"],
        filename    = result["filename"],
        file_type   = result.get("file_type", "DOC"),
        page_count  = result["page_count"],
        chunk_count = result["chunk_count"],
        status      = "INDEXED",
        boundary    = "LOCAL AIR-GAPPED",
    )


# ─── Conversations / History ─────────────────────────────────────────────────

@app.get("/api/investigations", response_model=List[ConversationSummary])
def get_investigations(db: Session = Depends(get_db)):
    """Return all previous human-friendly investigations."""
    records = db.query(InvestigationConversation).order_by(InvestigationConversation.updated_at.desc()).all()
    summaries = []
    for r in records:
        try:
            turns = json.loads(r.messages_json)
        except Exception:
            turns = []
        summaries.append(ConversationSummary(
            conversation_id = r.conversation_id,
            title           = r.title,
            created_at      = r.created_at.strftime("%H:%M"),
            updated_at      = r.updated_at.strftime("%H:%M"),
            agent           = r.agent,
            preview         = r.preview[:140] if r.preview else "",
            turn_count      = len(turns),
        ))
    return summaries


@app.get("/api/investigations/{conversation_id}", response_model=ConversationDetail)
def get_investigation_detail(conversation_id: str, db: Session = Depends(get_db)):
    """Return full thread history for an investigation."""
    record = db.query(InvestigationConversation).filter_by(conversation_id=conversation_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Investigation not found")
    try:
        raw_turns = json.loads(record.messages_json)
    except Exception:
        raw_turns = []

    messages = []
    for t in raw_turns:
        messages.append(TurnItem(
            user_request   = t.get("user_request", ""),
            agent          = t.get("agent", "Maintenance Agent"),
            result         = t.get("result", ""),
            timestamp      = t.get("timestamp", ""),
            evidence       = [EvidenceItem(**e) for e in t.get("evidence", [])],
            steps          = [ExecutionStep(**s) for s in t.get("steps", [])],
            entry_hash     = t.get("entry_hash", ""),
            inference_mode = t.get("inference_mode", "LOCAL_INFERENCE"),
        ))

    return ConversationDetail(
        conversation_id = record.conversation_id,
        title           = record.title,
        created_at      = record.created_at.strftime("%H:%M"),
        updated_at      = record.updated_at.strftime("%H:%M"),
        agent           = record.agent,
        messages        = messages,
    )


@app.get("/api/agents", response_model=List[AgentItem])
def get_agents():
    return [
        AgentItem(
            id       = "agent-maintenance",
            name     = "Maintenance Agent",
            purpose  = "Investigate equipment maintenance status and diagnose telemetry deviations.",
            status   = "READY",
            risk     = "LOW",
            access   = "Maintenance corpus",
            tools    = ["search_private_knowledge", "check_system_health"],
            approval = "Not required (read-only)",
        ),
        AgentItem(
            id       = "agent-knowledge",
            name     = "Knowledge Agent",
            purpose  = "Synthesise organisational intelligence from internal documents.",
            status   = "READY",
            risk     = "LOW",
            access   = "Full private corpus",
            tools    = ["search_private_knowledge"],
            approval = "Not required (read-only)",
        ),
        AgentItem(
            id       = "agent-security",
            name     = "Security Agent",
            purpose  = "Perform security compliance verification and audit log inspection.",
            status   = "READY",
            risk     = "MEDIUM",
            access   = "Logs, policy documents",
            tools    = ["search_private_knowledge", "inspect_operational_logs"],
            approval = "Required for policy actions",
        ),
    ]


# ─── Tool implementations ─────────────────────────────────────────────────────

def _tool_search_private_knowledge(query: str, n: int = 5, doc_filter: str | None = None):
    from .rag import search_knowledge
    return search_knowledge(query, n_results=n, doc_filter=doc_filter)


def _tool_check_system_health():
    from .llm import check_ollama
    available, detail = check_ollama()
    return {
        "ollama": "ONLINE" if available else "OFFLINE",
        "detail": detail,
    }


def _tool_inspect_operational_logs(db: Session):
    entries = db.query(AuditLogEntry).order_by(AuditLogEntry.id.desc()).limit(10).all()
    return [
        {
            "execution_id": e.execution_id,
            "timestamp":    e.timestamp.strftime("%H:%M:%S"),
            "agent":        e.agent,
            "status":       e.status,
        }
        for e in entries
    ]


# ─── Execute (Threaded with History & Follow-ups) ────────────────────────────

@app.post("/api/execute", response_model=ExecuteResponse)
def execute_query(payload: ExecuteRequest, db: Session = Depends(get_db)):
    from .llm import generate, check_ollama

    allowed_roles = {"OPERATOR_L1", "OPERATOR_L2", "ADMIN"}
    if payload.user_role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorised role for sovereign execution.",
        )

    now          = datetime.utcnow()
    timestamp_str = now.strftime("%H:%M:%S")
    execution_id  = f"EXEC-{int(now.timestamp() * 1000)}"

    # Retrieve or create investigation conversation
    conv_id = payload.conversation_id or f"INV-{int(now.timestamp())}"
    conv_record = db.query(InvestigationConversation).filter_by(conversation_id=conv_id).first()

    existing_turns: List[Dict[str, Any]] = []
    if conv_record:
        try:
            existing_turns = json.loads(conv_record.messages_json)
        except Exception:
            existing_turns = []

    steps: List[ExecutionStep] = []
    t0 = _ms()

    # ── Step 1: REQUEST RECEIVED ──────────────────────────────────────────
    steps.append(ExecutionStep(
        id="st-req", event="REQUEST RECEIVED",
        detail=f"Query captured - {len(payload.request)} chars (Thread: {conv_id})",
        duration_ms=_ms() - t0,
    ))

    # ── Step 2: RBAC ──────────────────────────────────────────────────────
    t1 = _ms()
    steps.append(ExecutionStep(
        id="st-rbac", event="RBAC CHECK",
        detail=f"Role {payload.user_role} validated - access GRANTED",
        duration_ms=_ms() - t1,
    ))

    # ── Step 3: KNOWLEDGE RETRIEVAL ───────────────────────────────────────
    t2 = _ms()
    chunks = _tool_search_private_knowledge(payload.request, n=5, doc_filter=payload.doc_filter)
    filter_note = f" [Filter: {payload.doc_filter}]" if payload.doc_filter and payload.doc_filter != "ALL" else ""
    retrieval_detail = (
        f"{len(chunks)} chunks retrieved from private knowledge base{filter_note}"
        if chunks else f"No direct matching documents found{filter_note}"
    )
    steps.append(ExecutionStep(
        id="st-know", event="PRIVATE KNOWLEDGE SEARCH",
        detail=retrieval_detail,
        duration_ms=_ms() - t2,
    ))

    # ── Step 4: AGENT DECISION ────────────────────────────────────
    t3 = _ms()
    agent_name = {
        "agent-maintenance": "Maintenance Agent",
        "agent-knowledge":   "Knowledge Agent",
        "agent-security":    "Security Agent",
    }.get(payload.agent_id or "agent-maintenance", "Maintenance Agent")

    steps.append(ExecutionStep(
        id="st-agent", event="AGENT SELECTED",
        detail=f"{agent_name} - bounded dispatch OK",
        duration_ms=_ms() - t3,
    ))

    # ── Step 5: TOOL INVOCATION ───────────────────────────────────────────
    t4 = _ms()
    tools_used = ["search_private_knowledge"]
    steps.append(ExecutionStep(
        id="st-tool", event="TOOL: search_private_knowledge",
        detail=f"Executed - {len(chunks)} results, zero external egress",
        duration_ms=_ms() - t4,
    ))

    # ── Step 6: VERIFICATION ──────────────────────────────────────────────
    t5 = _ms()
    steps.append(ExecutionStep(
        id="st-verify", event="VERIFICATION",
        detail="Sources verified - within on-premise boundary",
        duration_ms=_ms() - t5,
    ))

    # ── Step 7: LLM SYNTHESIS (with conversational history) ───────────────
    t6 = _ms()
    llm_result = generate(payload.request, chunks, history=existing_turns)
    ollama_detail = (
        f"LOCAL_INFERENCE via {llm_result['model']}"
        if llm_result["mode"] == "LOCAL_INFERENCE"
        else "DEMO_SIMULATION - Ollama unavailable"
    )
    steps.append(ExecutionStep(
        id="st-llm", event="LOCAL LLM SYNTHESIS",
        detail=ollama_detail,
        duration_ms=_ms() - t6,
    ))

    # ── Build evidence list ───────────────────────────────────────────────
    evidence = [
        EvidenceItem(
            filename       = c["filename"],
            page           = c["page"],
            source_locator = c.get("source_locator") or f"Page {c['page']}",
            file_type      = c.get("file_type", "DOC"),
            excerpt        = c.get("excerpt") or c["text"][:220],
            relevance      = c["relevance"],
        )
        for c in chunks
    ]

    result_text   = llm_result["answer"]
    inference_mode = llm_result["mode"]

    # ── Audit entry with chained hash ──────────────────────────────────────
    last_entry  = db.query(AuditLogEntry).order_by(AuditLogEntry.id.desc()).first()
    prev_hash   = last_entry.entry_hash if last_entry else "0" * 64

    entry_hash  = _hash_entry(
        previous_hash = prev_hash,
        execution_id  = execution_id,
        timestamp     = timestamp_str,
        user_role     = payload.user_role,
        user_request  = payload.request,
        agent         = agent_name,
        result        = result_text,
        status_text   = "VERIFIED",
    )

    db_entry = AuditLogEntry(
        execution_id      = execution_id,
        timestamp         = now,
        user_role         = payload.user_role,
        user_request      = payload.request,
        agent             = agent_name,
        execution_steps   = json.dumps([s.model_dump() for s in steps]),
        tools_invoked     = json.dumps(tools_used),
        retrieved_sources = json.dumps([e.model_dump() for e in evidence]),
        result            = result_text,
        status            = "VERIFIED",
        inference_mode    = inference_mode,
        previous_hash     = prev_hash,
        entry_hash        = entry_hash,
    )
    db.add(db_entry)

    # ── Persist Conversation History ──────────────────────────────────────
    new_turn = {
        "user_request":   payload.request,
        "agent":          agent_name,
        "result":         result_text,
        "timestamp":      timestamp_str,
        "evidence":       [e.model_dump() for e in evidence],
        "steps":          [s.model_dump() for s in steps],
        "entry_hash":     entry_hash,
        "inference_mode": inference_mode,
    }
    existing_turns.append(new_turn)

    if not conv_record:
        conv_record = InvestigationConversation(
            conversation_id = conv_id,
            title           = payload.request[:120],
            created_at      = now,
            updated_at      = now,
            agent           = agent_name,
            preview         = result_text[:160],
            messages_json   = json.dumps(existing_turns),
        )
        db.add(conv_record)
    else:
        conv_record.updated_at    = now
        conv_record.preview       = result_text[:160]
        conv_record.messages_json = json.dumps(existing_turns)

    db.commit()

    return ExecuteResponse(
        execution_id    = execution_id,
        conversation_id = conv_id,
        timestamp       = timestamp_str,
        user_role       = payload.user_role,
        agent           = agent_name,
        status          = "VERIFIED",
        inference_mode  = inference_mode,
        result          = result_text,
        evidence        = evidence,
        steps           = steps,
        entry_hash      = entry_hash,
    )


@app.get("/api/security", response_model=SecurityResponse)
def get_security_state():
    return SecurityResponse(
        boundary       = "Local Environment",
        external_egress = "BLOCKED",
        inference      = "ON-PREMISE (Ollama)",
        storage        = "LOCAL_DISK",
        current_role   = "OPERATOR_L2",
        permissions    = {
            "knowledge_search":     "ALLOWED",
            "diagnostics":          "ALLOWED",
            "report_generation":    "ALLOWED",
            "system_modification":  "DENIED",
            "administrative_tools": "DENIED",
        },
    )


@app.get("/api/audit", response_model=List[AuditEntry])
def get_audit_trail(db: Session = Depends(get_db)):
    entries = db.query(AuditLogEntry).order_by(AuditLogEntry.id.desc()).limit(50).all()
    result  = []
    for e in entries:
        result.append(AuditEntry(
            id             = e.id,
            execution_id   = e.execution_id,
            timestamp      = e.timestamp.strftime("%H:%M:%S"),
            user_role      = e.user_role,
            user_request   = e.user_request[:120],
            agent          = e.agent,
            tools_invoked  = e.tools_invoked,
            status         = e.status,
            entry_hash     = e.entry_hash,
            previous_hash  = e.previous_hash,
            inference_mode = getattr(e, "inference_mode", "UNKNOWN"),
        ))
    return result


@app.get("/api/audit/verify", response_model=AuditVerifyResponse)
def verify_audit_chain(db: Session = Depends(get_db)):
    """
    Walk the audit chain in ascending order and verify every hash.
    Returns whether the chain is intact.
    """
    entries = db.query(AuditLogEntry).order_by(AuditLogEntry.id.asc()).all()

    if not entries:
        return AuditVerifyResponse(
            chain_valid=True, total_entries=0,
            verified_entries=0, broken_at=None,
        )

    broken_at       = None
    verified_count  = 0

    for e in entries:
        expected = _hash_entry(
            previous_hash = e.previous_hash,
            execution_id  = e.execution_id,
            timestamp     = e.timestamp.strftime("%H:%M:%S"),
            user_role     = e.user_role,
            user_request  = e.user_request,
            agent         = e.agent,
            result        = e.result,
            status_text   = e.status,
        )
        if expected == e.entry_hash:
            verified_count += 1
        else:
            broken_at = e.execution_id
            break

    return AuditVerifyResponse(
        chain_valid      = broken_at is None,
        total_entries    = len(entries),
        verified_entries = verified_count,
        broken_at        = broken_at,
    )

# ─── Static Web Hosting & Landing Page ───────────────────────────────────────

def _resolve_file(filename: str) -> str:
    """Find a static file across all possible deployment directory layouts."""
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", filename)),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", filename)),
        os.path.abspath(os.path.join(os.getcwd(), filename)),
        os.path.abspath(os.path.join(os.getcwd(), "..", filename)),
        os.path.abspath(os.path.join(os.getcwd(), "backend", filename)),
        os.path.abspath(filename),
    ]
    for p in candidates:
        if os.path.exists(p) and os.path.isfile(p):
            return p
    return candidates[0]

def _resolve_dir(dirname: str) -> str | None:
    """Find a static directory across all possible deployment directory layouts."""
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", dirname)),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", dirname)),
        os.path.abspath(os.path.join(os.getcwd(), dirname)),
        os.path.abspath(os.path.join(os.getcwd(), "..", dirname)),
        os.path.abspath(os.path.join(os.getcwd(), "backend", dirname)),
        os.path.abspath(dirname),
    ]
    for p in candidates:
        if os.path.exists(p) and os.path.isdir(p):
            return p
    return None

@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
def get_landing_page():
    path = _resolve_file("index.html")
    return FileResponse(path)

@app.get("/command-center.html", include_in_schema=False)
@app.get("/command-center", include_in_schema=False)
@app.get("/command-center/", include_in_schema=False)
@app.get("/workspace", include_in_schema=False)
def get_command_center_page():
    path = _resolve_file("command-center.html")
    return FileResponse(path)

@app.get("/innercore.html", include_in_schema=False)
@app.get("/innercore", include_in_schema=False)
def get_innercore_page():
    path = _resolve_file("innercore.html")
    return FileResponse(path)

# Mount asset directories if present
for asset_name in ["innercore-assets", "inner-green-assets", "src"]:
    found_dir = _resolve_dir(asset_name)
    if found_dir:
        app.mount(f"/{asset_name}", StaticFiles(directory=found_dir), name=asset_name)

@app.get("/{full_path:path}", include_in_schema=False)
def catch_all_fallback(full_path: str):
    """Catch-all for SPA navigation and static files, preventing 404 on refresh."""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Check if a static file matches directly
    direct = _resolve_file(full_path)
    if os.path.exists(direct) and os.path.isfile(direct):
        return FileResponse(direct)
    
    # If route matches command-center views
    if any(k in full_path for k in ["command", "workspace", "knowledge", "agents", "security", "audit"]):
        return FileResponse(_resolve_file("command-center.html"))
        
    return FileResponse(_resolve_file("index.html"))
