from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class HealthResponse(BaseModel):
    status: str
    boundary: str
    inference_mode: str
    database: str


# ─── System mode ─────────────────────────────────────────────────────────────

class SystemModeResponse(BaseModel):
    ollama_available: bool
    ollama_models: str
    embed_model: str
    chroma_docs: int
    inference_mode: str   # "LOCAL_INFERENCE" | "DEMO_SIMULATION"


# ─── Knowledge / documents ───────────────────────────────────────────────────

class DocumentItem(BaseModel):
    id: str
    title: str
    meta: str
    status: str


class UploadedDocument(BaseModel):
    doc_id: str
    filename: str
    file_type: Optional[str] = "PDF"
    page_count: int
    chunk_count: int
    status: str
    boundary: Optional[str] = "LOCAL AIR-GAPPED"


class ChunkExcerpt(BaseModel):
    page: int
    chunk_idx: int
    text: str


class DocumentDetailsResponse(BaseModel):
    filename: str
    doc_id: str
    page_count: int
    chunk_count: int
    status: str
    boundary: str = "LOCAL AIR-GAPPED"
    excerpts: List[ChunkExcerpt]


# ─── Agents ──────────────────────────────────────────────────────────────────

class AgentItem(BaseModel):
    id: str
    name: str
    purpose: str
    status: str
    risk: str
    access: str
    tools: List[str]
    approval: str


# ─── Execute & Conversations ─────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    request: str
    user_role: Optional[str] = "OPERATOR_L2"
    agent_id: Optional[str]  = "agent-maintenance"
    conversation_id: Optional[str] = None
    doc_filter: Optional[str] = None


class EvidenceItem(BaseModel):
    filename: str
    page: int
    source_locator: Optional[str] = None
    file_type: Optional[str] = "DOC"
    excerpt: str
    relevance: float


class ExecutionStep(BaseModel):
    id: str
    event: str
    detail: str
    duration_ms: int


class ExecuteResponse(BaseModel):
    execution_id: str
    conversation_id: Optional[str] = None
    timestamp: str
    user_role: str
    agent: str
    status: str
    inference_mode: str          # "LOCAL_INFERENCE" | "DEMO_SIMULATION"
    result: str
    evidence: List[EvidenceItem]
    steps: List[ExecutionStep]
    entry_hash: str


class TurnItem(BaseModel):
    user_request: str
    agent: str
    result: str
    timestamp: str
    evidence: List[EvidenceItem] = []
    steps: List[ExecutionStep] = []
    entry_hash: str = ""
    inference_mode: str = "LOCAL_INFERENCE"


class ConversationSummary(BaseModel):
    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    agent: str
    preview: str
    turn_count: int


class ConversationDetail(BaseModel):
    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    agent: str
    messages: List[TurnItem]


# ─── Security ────────────────────────────────────────────────────────────────

class SecurityResponse(BaseModel):
    boundary: str
    external_egress: str
    inference: str
    storage: str
    current_role: str
    permissions: Dict[str, Any]


# ─── Audit ───────────────────────────────────────────────────────────────────

class AuditEntry(BaseModel):
    id: int
    execution_id: str
    timestamp: str
    user_role: str
    user_request: str
    agent: str
    tools_invoked: str
    status: str
    entry_hash: str
    previous_hash: str
    inference_mode: str

    class Config:
        from_attributes = True


class AuditVerifyResponse(BaseModel):
    chain_valid: bool
    total_entries: int
    verified_entries: int
    broken_at: Optional[str]