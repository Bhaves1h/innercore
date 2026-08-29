from sqlalchemy import Column, Integer, String, Text, DateTime
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
    created_at      = Column(DateTime,    default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    agent           = Column(String(64),  default="Maintenance Agent", nullable=False)
    preview         = Column(Text,        default="")
    messages_json   = Column(Text,        default="[]", nullable=False)