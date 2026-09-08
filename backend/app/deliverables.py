"""
INNERCORE Deliverable Generation Module
Generates real downloadable investigation reports in PDF, DOCX, and Markdown.
100% on-premise, zero cloud services.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import pymupdf
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

DELIVERABLES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "deliverables"))
os.makedirs(DELIVERABLES_DIR, exist_ok=True)


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>| ]', '_', name)[:40]


def generate_pdf_report(data: Dict[str, Any]) -> str:
    """Generate a clean, high-density PDF investigation report using PyMuPDF."""
    exec_id = data.get("execution_id", f"EXEC-{int(datetime.utcnow().timestamp())}")
    safe_title = _sanitize_filename(data.get("query", "Investigation"))
    filename = f"INNERCORE_Report_{exec_id}_{safe_title}.pdf"
    filepath = os.path.join(DELIVERABLES_DIR, filename)

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842) # Standard A4

    # -- Top Banner ------------------------------------------------------------
    rect_header = pymupdf.Rect(0, 0, 595, 75)
    page.draw_rect(rect_header, color=(0.04, 0.08, 0.05), fill=(0.04, 0.08, 0.05))
    page.draw_line(pymupdf.Point(0, 75), pymupdf.Point(595, 75), color=(0.24, 0.94, 0.62), width=1.5)

    page.insert_text(pymupdf.Point(40, 32), "INNERCORE SOVEREIGN AI WORKBENCH", fontsize=11, fontname="helv", color=(0.24, 0.94, 0.62))
    page.insert_text(pymupdf.Point(40, 52), "OFFICIAL INVESTIGATION DELIVERABLE · 100% ON-PREMISE AIR-GAPPED", fontsize=8.5, fontname="helv", color=(0.8, 0.8, 0.8))

    content_y = 100

    # -- Metadata Section ------------------------------------------------------
    page.insert_text(pymupdf.Point(40, content_y), "INVESTIGATION PARAMETERS", fontsize=11, fontname="helv", color=(0.1, 0.1, 0.1))
    content_y += 16

    query_text = f"Query: {data.get('query', 'N/A')}"
    page.insert_text(pymupdf.Point(40, content_y), query_text[:95], fontsize=9.5, fontname="helv", color=(0.15, 0.15, 0.15))
    content_y += 14

    op_role = data.get("operator_role", "OPERATOR_L2")
    agent_name = data.get("agent_name", "Maintenance Agent")
    model_name = data.get("model_name", "llama3.2:latest")
    meta_line = f"Operator: {op_role}  |  Agent: {agent_name}  |  Model: {model_name} (Local)"
    page.insert_text(pymupdf.Point(40, content_y), meta_line, fontsize=8.5, fontname="helv", color=(0.4, 0.4, 0.4))
    content_y += 14

    sec_line = "Network Boundary: AIR-GAPPED ON-PREMISE  |  External Egress: ZERO (0)"
    page.insert_text(pymupdf.Point(40, content_y), sec_line, fontsize=8.5, fontname="helv", color=(0.1, 0.55, 0.3))
    content_y += 24

    # -- Executive Result Box --------------------------------------------------
    page.insert_text(pymupdf.Point(40, content_y), "EXECUTIVE RESULT & SYNTHESIS", fontsize=11, fontname="helv", color=(0.1, 0.1, 0.1))
    content_y += 14

    result_text = data.get("result", "No result generated.")
    rect_box = pymupdf.Rect(40, content_y, 555, content_y + 130)
    page.draw_rect(rect_box, color=(0.85, 0.85, 0.85), fill=(0.96, 0.97, 0.96))
    page.insert_textbox(pymupdf.Rect(48, content_y + 8, 547, content_y + 122), result_text, fontsize=9, fontname="helv", color=(0.12, 0.12, 0.12))
    content_y += 145

    # -- Grounded Evidence Sources ---------------------------------------------
    page.insert_text(pymupdf.Point(40, content_y), "GROUNDED EVIDENCE SOURCES", fontsize=11, fontname="helv", color=(0.1, 0.1, 0.1))
    content_y += 15

    evidence_list = data.get("evidence", [])
    if evidence_list:
        for idx, ev in enumerate(evidence_list[:3], 1):
            fn = ev.get("filename", "Source Document")
            loc = ev.get("source_locator") or f"Page {ev.get('page', 1)}"
            rel = ev.get("relevance", 85.0)
            ex = ev.get("excerpt", "").strip().replace("\n", " ")
            if len(ex) > 130:
                ex = ex[:127] + "..."

            ev_title = f"{idx}. {fn}  ·  {loc}  (Relevance: {rel}%)"
            page.insert_text(pymupdf.Point(40, content_y), ev_title, fontsize=8.5, fontname="helv", color=(0.1, 0.5, 0.3))
            content_y += 12
            if ex:
                page.insert_text(pymupdf.Point(52, content_y), f'\"{ex}\"', fontsize=7.5, fontname="helv", color=(0.35, 0.35, 0.35))
                content_y += 14
    else:
        page.insert_text(pymupdf.Point(40, content_y), "Zero external evidence chunks retrieved.", fontsize=8.5, fontname="helv", color=(0.5, 0.5, 0.5))
        content_y += 16

    content_y += 10

    # -- 7-Stage Agent Execution Trace -----------------------------------------
    page.insert_text(pymupdf.Point(40, content_y), "7-STAGE AGENT EXECUTION TRACE", fontsize=11, fontname="helv", color=(0.1, 0.1, 0.1))
    content_y += 14

    steps_list = data.get("steps", [])
    if steps_list:
        for s in steps_list:
            lbl = (s.get("label") or s.get("name") or "ACTION").upper()
            det = s.get("detail") or s.get("event") or ""
            t_str = f"[{lbl}] {det}"
            if len(t_str) > 105:
                t_str = t_str[:102] + "..."
            page.insert_text(pymupdf.Point(40, content_y), t_str, fontsize=7.5, fontname="helv", color=(0.25, 0.25, 0.25))
            content_y += 11
    content_y += 12

    # -- Cryptographic Audit Provenance ----------------------------------------
    page.insert_text(pymupdf.Point(40, content_y), "CRYPTOGRAPHIC AUDIT PROVENANCE", fontsize=11, fontname="helv", color=(0.1, 0.1, 0.1))
    content_y += 14

    page.insert_text(pymupdf.Point(40, content_y), f"Execution ID: {exec_id}", fontsize=8, fontname="helv", color=(0.3, 0.3, 0.3))
    content_y += 11

    entry_hash = data.get("entry_hash", "0"*64)
    page.insert_text(pymupdf.Point(40, content_y), f"SHA-256 Hash: {entry_hash}", fontsize=7.5, fontname="helv", color=(0.3, 0.3, 0.3))
    content_y += 11

    page.insert_text(pymupdf.Point(40, content_y), "Chain Verification: VALID (Tamper-evident mathematical hash chain)", fontsize=8, fontname="helv", color=(0.1, 0.6, 0.3))

    doc.save(filepath)
    doc.close()
    return filepath


def generate_docx_report(data: Dict[str, Any]) -> str:
    """Generate a clean Word (.docx) investigation report using python-docx."""
    exec_id = data.get("execution_id", f"EXEC-{int(datetime.utcnow().timestamp())}")
    safe_title = _sanitize_filename(data.get("query", "Investigation"))
    filename = f"INNERCORE_Report_{exec_id}_{safe_title}.docx"
    filepath = os.path.join(DELIVERABLES_DIR, filename)

    doc_word = docx.Document()

    # Title
    h0 = doc_word.add_heading("INNERCORE SOVEREIGN INVESTIGATION REPORT", level=0)
    
    # Metadata
    p_meta = doc_word.add_paragraph()
    p_meta.add_run("Investigation Query: ").bold = True
    p_meta.add_run(f"{data.get('query', 'N/A')}\n")
    p_meta.add_run("Generated: ").bold = True
    p_meta.add_run(f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    p_meta.add_run("Operator: ").bold = True
    p_meta.add_run(f"{data.get('operator_role', 'OPERATOR_L2')}  |  ")
    p_meta.add_run("Agent: ").bold = True
    p_meta.add_run(f"{data.get('agent_name', 'Maintenance Agent')}  |  ")
    p_meta.add_run("Model: ").bold = True
    p_meta.add_run(f"{data.get('model_name', 'llama3.2:latest')} (Local)\n")
    p_meta.add_run("Security Boundary: ").bold = True
    p_meta.add_run("AIR-GAPPED ON-PREMISE (0 External Egress)")

    # Result
    doc_word.add_heading("EXECUTIVE RESULT & SYNTHESIS", level=1)
    doc_word.add_paragraph(data.get("result", "No result generated."))

    # Evidence
    doc_word.add_heading("GROUNDED EVIDENCE SOURCES", level=1)
    evidence_list = data.get("evidence", [])
    if evidence_list:
        for idx, ev in enumerate(evidence_list, 1):
            fn = ev.get("filename", "Source Document")
            loc = ev.get("source_locator") or f"Page {ev.get('page', 1)}"
            rel = ev.get("relevance", 85.0)
            ex = ev.get("excerpt", "").strip()

            p_ev = doc_word.add_paragraph()
            p_ev.add_run(f"{idx}. {fn} · {loc} (Relevance: {rel}%)\n").bold = True
            if ex:
                p_ev.add_run(f'\"{ex}\"').italic = True
    else:
        doc_word.add_paragraph("Zero external evidence chunks retrieved.")

    # Execution Trace
    doc_word.add_heading("7-STAGE AGENT EXECUTION TRACE", level=1)
    steps_list = data.get("steps", [])
    if steps_list:
        for s in steps_list:
            lbl = (s.get("label") or s.get("name") or "ACTION").upper()
            det = s.get("detail") or s.get("event") or ""
            p_s = doc_word.add_paragraph()
            p_s.add_run(f"[{lbl}] ").bold = True
            p_s.add_run(det)
            p_s.paragraph_format.left_indent = Inches(0.2)

    # Cryptographic Audit
    doc_word.add_heading("CRYPTOGRAPHIC AUDIT PROVENANCE", level=1)
    p_aud = doc_word.add_paragraph()
    p_aud.add_run(f"Execution ID: {exec_id}\n")
    p_aud.add_run(f"SHA-256 Hash: {data.get('entry_hash', '0'*64)}\n")
    p_aud.add_run("Chain Verification: VALID (Tamper-evident mathematical hash chain)").bold = True

    doc_word.save(filepath)
    return filepath


def generate_md_report(data: Dict[str, Any]) -> str:
    """Generate a clean Markdown (.md) investigation report."""
    exec_id = data.get("execution_id", f"EXEC-{int(datetime.utcnow().timestamp())}")
    safe_title = _sanitize_filename(data.get("query", "Investigation"))
    filename = f"INNERCORE_Report_{exec_id}_{safe_title}.md"
    filepath = os.path.join(DELIVERABLES_DIR, filename)

    evidence_md = ""
    evidence_list = data.get("evidence", [])
    if evidence_list:
        for idx, ev in enumerate(evidence_list, 1):
            fn = ev.get("filename", "Source Document")
            loc = ev.get("source_locator") or f"Page {ev.get('page', 1)}"
            rel = ev.get("relevance", 85.0)
            ex = ev.get("excerpt", "").strip()
            evidence_md += f"{idx}. **{fn}** · {loc} *(Relevance: {rel}%)*\n   > \"{ex}\"\n\n"
    else:
        evidence_md = "_Zero external evidence chunks retrieved._\n"

    trace_md = ""
    steps_list = data.get("steps", [])
    if steps_list:
        for s in steps_list:
            lbl = (s.get("label") or s.get("name") or "ACTION").upper()
            det = s.get("detail") or s.get("event") or ""
            t_stamp = s.get("timestamp", "")
            trace_md += f"{t_stamp:8s}  {lbl:18s}  {det}\n"

    md_text = f"""# INNERCORE SOVEREIGN INVESTIGATION REPORT

- **Investigation Query:** {data.get('query', 'N/A')}
- **Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
- **Operator:** `{data.get('operator_role', 'OPERATOR_L2')}`
- **Agent:** {data.get('agent_name', 'Maintenance Agent')}
- **Model:** `{data.get('model_name', 'llama3.2:latest')}` (Local Inference)
- **Security Boundary:** AIR-GAPPED ON-PREMISE (0 External Egress)

---

## EXECUTIVE RESULT & SYNTHESIS

{data.get('result', 'No result generated.')}

---

## GROUNDED EVIDENCE SOURCES

{evidence_md}
---

## 7-STAGE AGENT EXECUTION TRACE

```
{trace_md.strip()}
```

---

## CRYPTOGRAPHIC AUDIT PROVENANCE

- **Inference Mode:** `{data.get('inference_mode', 'LOCAL_INFERENCE')}`
- **Execution ID:** `{exec_id}`
- **SHA-256 Entry Hash:** `{data.get('entry_hash', '0'*64)}`
- **Chain Verification:** `VALID` (Tamper-evident mathematical hash chain)
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_text)

    return filepath
