from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime
from .database import Base


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id              = Column(Integer,     primary_key=True, index=True)
    execution_id    = Column(String(64),  unique=True, index=True, nullable=False)
    timestamp       = Column(DateTime,    default=datetime.utcnow, nullable=False)
    user_role       = Column(String(32),  nullable=False)
    user_request    = Column(Text,        nullable=False)
    agent           = Column(String(64),  nullable=False)
    execution_steps = Column(Text,        nullable=False)
    tools_invoked   = Column(Text,        nullable=False)
    retrieved_sources = Column(Text,      nullable=False)
    result          = Column(Text,        nullable=False)
    status          = Column(String(32),  nullable=False)
    inference_mode  = Column(String(32),  nullable=False, default="UNKNOWN")
    previous_hash   = Column(String(64),  nullable=False)
    entry_hash      = Column(String(64),  nullable=False)


class InvestigationConversation(Base):
    __tablename__ = "investigations"

    id              = Column(Integer,     primary_key=True, index=True)
    conversation_id = Column(String(64),  unique=True, index=True, nullable=False)
    title           = Column(String(256), nullable=False)
    question        = Column(Text,        default="")
    answer          = Column(Text,        default="")
    model           = Column(String(64),  default="llama3.2:latest")
    agent           = Column(String(64),  default="Maintenance Agent", nullable=False)
    collection      = Column(String(64),  default="All Documents")
    status          = Column(String(32),  default="VERIFIED")
    preview         = Column(Text,        default="")
    messages_json   = Column(Text,        default="[]", nullable=False)
    execution_trace = Column(Text,        default="[]")
    created_at      = Column(DateTime,    default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class InvestigationEvidence(Base):
    __tablename__ = "investigation_evidence"

    id               = Column(Integer,     primary_key=True, index=True)
    investigation_id = Column(String(64),  index=True, nullable=False)
    filename         = Column(String(128), nullable=False)
    page             = Column(Integer,     default=1)
    excerpt          = Column(Text,        default="")
    relevance        = Column(Float,       default=0.0)
    created_at       = Column(DateTime,    default=datetime.utcnow, nullable=False)


class KnowledgeCollection(Base):
    __tablename__ = "knowledge_collections"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(64), unique=True, index=True, nullable=False)
    description = Column(String(256), default="")
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)


class DocumentRecord(Base):
    __tablename__ = "document_records"

    id          = Column(Integer, primary_key=True, index=True)
    filename    = Column(String(128), unique=True, index=True, nullable=False)
    collection  = Column(String(64), default="All Documents", nullable=False)
    file_type   = Column(String(16), default="PDF")
    page_count  = Column(Integer, default=1)
    chunk_count = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)