# INNERCORE SOVEREIGN INVESTIGATION REPORT

- **Investigation Query:** What is INNERCORE's revenue model?
- **Generated:** 2026-09-01 10:43:25 UTC
- **Operator:** `OPERATOR_L2`
- **Agent:** Knowledge Agent
- **Model:** `llama3.2:latest` (Local Inference)
- **Security Boundary:** AIR-GAPPED ON-PREMISE (0 External Egress)

---

## EXECUTIVE RESULT & SYNTHESIS

ANSWER

INNERCORE's revenue model is likely a license/maintenance model, where a per-seat or perpetual on-prem license for the software is sold, accompanied by annual support. Additionally, professional services for installation, customization, and other related needs are also offered.

SOURCES
uploaded_exec_summary.pdf, Page 9 (relevance 71.2%)

---

## GROUNDED EVIDENCE SOURCES

1. **uploaded_exec_summary.pdf** · Page 9 *(Relevance: 71.2%)*
   > "Revenue Model: Likely a license/maintenance model: e.g. a per-seat or perpetual on-prem license
for the software + annual support."

2. **Executive Summary.pdf** · Page 9 *(Relevance: 71.2%)*
   > "Revenue Model: Likely a license/maintenance model: e.g. a per-seat or perpetual on-prem license
for the software + annual support."

3. **uploaded_exec_summary.pdf** · Page 11 *(Relevance: 60.4%)*
   > "A final slide
might read: 
INNERCORE
Intelligence That Stays Within
or 
RAKSHA - Sovereign Industrial AI Workbench
with a one-sentence description, e.g."

4. **Executive Summary.pdf** · Page 11 *(Relevance: 60.4%)*
   > "A final slide
might read: 
INNERCORE
Intelligence That Stays Within
or 
RAKSHA - Sovereign Industrial AI Workbench
with a one-sentence description, e.g."

5. **uploaded_exec_summary.pdf** · Page 8 *(Relevance: 60.0%)*
   > "* 
* 
* 
* 
Aug
Aug
Aug
Sep
Sep
Sep
Sep
Sep
Sep
Sep
Sep
Sep
Sep
Sep
Sep
Sep
Initial Setup (env, models)
Document Ingestion & Indexing
Agent Workflow (core QA)
UI Basic + Demo Scenario
Extend Agents (summarize, report)
Add Vision/OCR Pipelin…"


---

## 7-STAGE AGENT EXECUTION TRACE

```
10:43:22  TASK INTAKE         Role OPERATOR_L2 verified · Boundary: On-premise air-gapped
10:43:22  MODEL ROUTER        Task: DOCUMENT_ANALYSIS · Optimal local model for structured document investigation & RAG retrieval (Matched preference: llama3.2:latest)
10:43:22  AGENT PLANNING      Knowledge Agent planned investigation: 1. Hybrid semantic retrieval across private corpus, 2. Grounded local synthesis
10:43:22  KNOWLEDGE SEARCH    Global Corpus · Retrieved 5 relevant passages from uploaded_exec_summary.pdf (Page 9)
10:43:22  TOOL EXECUTION      Executed semantic_evidence_verifier: 5 chunks analyzed for relevance
10:43:22  VERIFY              All sources & parameters verified on-premise · Zero external cloud egress
10:43:24  RESULT              Inference complete (LOCAL_INFERENCE) via llama3.2:latest
```

---

## CRYPTOGRAPHIC AUDIT PROVENANCE

- **Inference Mode:** `LOCAL_INFERENCE`
- **Execution ID:** `EXEC-1788239602182`
- **SHA-256 Entry Hash:** `4689770ba0cc7999395acddb31171124e623971ffe9092151598a39bb44f8ee0`
- **Chain Verification:** `VALID` (Tamper-evident mathematical hash chain)
