from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union


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
    collection: Optional[str] = "All Documents"


class KnowledgeCollectionItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    document_count: int = 0
    chunk_count: int = 0
    created_at: Optional[str] = None


class CreateCollectionRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class AssignCollectionRequest(BaseModel):
    filename: str
    collection: str


class UploadedDocument(BaseModel):
    success: bool = True
    doc_id: str
    filename: str
    file_type: Optional[str] = "PDF"
    collection: Optional[str] = "All Documents"
    page_count: int
    chunk_count: int
    chunks: Optional[int] = None
    status: str
    boundary: Optional[str] = "LOCAL AIR-GAPPED"


class ChunkExcerpt(BaseModel):
    page: int
    chunk_idx: int
    text: str


class DocumentDetailsResponse(BaseModel):
    filename: str
    doc_id: str
    collection: Optional[str] = "All Documents"
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

class ApprovalRequestInfo(BaseModel):
    approval_id: str
    agent: str = "Maintenance Agent"
    action: str
    target: str
    risk: str = "MEDIUM"              # "LOW" | "MEDIUM" | "HIGH"
    reason: str
    role_required: str = "OPERATOR_L2"
    status: str = "PENDING"           # "PENDING" | "APPROVED" | "DENIED"
    decision: Optional[str] = None


class ExecuteRequest(BaseModel):
    request: str
    user_role: Optional[str] = "OPERATOR_L2"
    agent_id: Optional[str]  = "agent-maintenance"
    conversation_id: Optional[str] = None
    doc_filter: Optional[str] = None
    collection_filter: Optional[str] = None
    approval_id: Optional[str] = None
    approval_decision: Optional[str] = None   # "APPROVED" | "DENIED"


class EvidenceItem(BaseModel):
    filename: str
    page: int
    source_locator: Optional[str] = None
    file_type: Optional[str] = "DOC"
    collection: Optional[str] = "All Documents"
    excerpt: str
    relevance: float


class ExecutionStep(BaseModel):
    id: str
    name: Optional[str] = None
    label: Optional[str] = None
    event: str
    detail: str
    status: Optional[str] = "completed"
    timestamp: Optional[str] = None
    duration_ms: int = 0


class ModelItem(BaseModel):
    name: str
    available: bool = True
    size: Optional[str] = None
    parameter_size: Optional[str] = None
    quantization: Optional[str] = None
    family: Optional[str] = None
    boundary: Optional[str] = "LOCAL AIR-GAPPED"


class ModelsResponse(BaseModel):
    runtime: str = "ollama"
    status: str = "online"
    host: str = "127.0.0.1:11434"
    boundary: str = "LOCAL AIR-GAPPED"
    models: List[ModelItem] = []
    count: int = 0


class ModelRoutingInfo(BaseModel):
    selected_model: str
    runtime: str = "Ollama · Local"
    task_type: str = "GENERAL_QUERY"
    reason: str
    available_models_count: int = 1
    available_models: List[str] = []
    network_boundary: str = "LOCAL AIR-GAPPED"
    status: str = "online"


class ExecuteResponse(BaseModel):
    execution_id: str
    conversation_id: Optional[str] = None
    timestamp: str
    user_role: str
    agent: str
    model: Optional[str] = "llama3.2:latest"
    model_routing: Optional[ModelRoutingInfo] = None
    status: str
    inference_mode: str          # "LOCAL_INFERENCE" | "DEMO_SIMULATION"
    result: str
    evidence: List[EvidenceItem]
    steps: List[ExecutionStep]
    tools_invoked: Optional[List[str]] = []
    entry_hash: str
    approval_request: Optional[ApprovalRequestInfo] = None


class TurnItem(BaseModel):
    user_request: str
    agent: str
    result: str
    timestamp: str
    evidence: List[EvidenceItem] = []
    steps: List[ExecutionStep] = []
    entry_hash: str = ""
    inference_mode: str = "LOCAL_INFERENCE"
    execution_id: Optional[str] = None
    approval_request: Optional[ApprovalRequestInfo] = None
    approval_decision: Optional[str] = None


class InvestigationEvidenceItem(BaseModel):
    id: Optional[int] = None
    investigation_id: Optional[str] = None
    filename: str
    page: int = 1
    excerpt: str = ""
    relevance: float = 0.0


class ConversationSummary(BaseModel):
    id: Optional[Union[int, str]] = None
    conversation_id: str
    title: str
    question: Optional[str] = ""
    answer: Optional[str] = ""
    model: Optional[str] = "llama3.2:latest"
    collection: Optional[str] = "All Documents"
    status: Optional[str] = "VERIFIED"
    created_at: str
    updated_at: str
    agent: str
    preview: str
    turn_count: int = 1
    date_group: Optional[str] = "Today"


class ConversationDetail(BaseModel):
    id: Optional[Union[int, str]] = None
    conversation_id: str
    title: str
    question: Optional[str] = ""
    answer: Optional[str] = ""
    model: Optional[str] = "llama3.2:latest"
    collection: Optional[str] = "All Documents"
    status: Optional[str] = "VERIFIED"
    created_at: str
    updated_at: str
    agent: str
    messages: List[TurnItem] = []
    evidence: List[EvidenceItem] = []
    steps: List[ExecutionStep] = []


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
    verified_entries: Optional[int] = 0
    first_hash: Optional[str] = ""
    last_hash: Optional[str] = ""
    broken_at: Optional[str] = None
    broken_at_id: Optional[int] = None


# ─── Deliverables ────────────────────────────────────────────────────────────

class GenerateReportRequest(BaseModel):
    conversation_id: Optional[str] = None
    execution_id: Optional[str] = None
    query: Optional[str] = None
    result: Optional[str] = None
    evidence: Optional[List[Dict[str, Any]]] = []
    steps: Optional[List[Dict[str, Any]]] = []
    format: str = "pdf"             # "pdf" | "docx" | "md"
    user_role: Optional[str] = "OPERATOR_L2"
    agent: Optional[str] = "Maintenance Agent"
    model: Optional[str] = "llama3.2:latest"


class DeliverableResponse(BaseModel):
    success: bool
    format: str
    filename: str
    download_url: str
    file_size: str
    generated_at: str