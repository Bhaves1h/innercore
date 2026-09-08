# INNERCORE SOVEREIGN INVESTIGATION REPORT

- **Investigation Query:** What is INNERCORE's revenue model?
- **Generated:** 2026-09-01 09:49:01 UTC
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
09:48:51  TASK INTAKE         Role OPERATOR_L2 verified · Boundary: On-premise air-gapped
09:48:51  MODEL ROUTER        Task: DOCUMENT_ANALYSIS · Optimal local model for structured document investigation & RAG retrieval (Matched preference: llama3.2:latest)
09:48:51  AGENT PLANNING      Knowledge Agent planned investigation: 1. Hybrid semantic retrieval across private corpus, 2. Grounded local synthesis
09:48:52  KNOWLEDGE SEARCH    Retrieved 5 relevant passages from uploaded_exec_summary.pdf (Page 9)
09:48:52  TOOL EXECUTION      Executed semantic_evidence_verifier: 5 chunks analyzed for relevance
09:48:52  VERIFY              All sources verified on-premise · Zero external cloud egress
09:49:00  RESULT              Inference complete (LOCAL_INFERENCE) via llama3.2:latest
```

---

## CRYPTOGRAPHIC AUDIT PROVENANCE

- **Inference Mode:** `LOCAL_INFERENCE`
- **Execution ID:** `EXEC-1788236331599`
- **SHA-256 Entry Hash:** `125582ecf50638cb012bc9537fe60a651c4a08718381746588c7c928d1d57341`
- **Chain Verification:** `VALID` (Tamper-evident mathematical hash chain)
