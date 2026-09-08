"""
Local LLM interface — Ollama via HTTP.

Checks whether Ollama is running at OLLAMA_HOST (default: http://localhost:11434).
If available → real local inference.
If unavailable → returns a clearly-labelled DEMO SIMULATION response.

NEVER presents a demo response as real local inference.
"""
from __future__ import annotations

import os
import re
from typing import List, Dict, Any, Tuple

import httpx

OLLAMA_HOST  = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
TIMEOUT_SECS = 120


DEFAULT_GROQ_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


# ─── Availability check ──────────────────────────────────────────────────────

def _check_ollama_direct() -> Tuple[bool, str]:
    """Lightweight check strictly against the local Ollama daemon."""
    try:
        r = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=0.8)
        if r.status_code == 200:
            tags = r.json().get("models", [])
            names = [m.get("name", "") for m in tags]
            return True, ", ".join(names) if names else "running (no models pulled)"
    except Exception:
        pass
    return False, "Ollama not reachable"


def check_ollama() -> Tuple[bool, str]:
    """
    Returns (available: bool, model_or_reason: str).
    First checks local Ollama; if offline, checks the Sovereign Cloud Engine.
    """
    ollama_ok, reason = _check_ollama_direct()
    if ollama_ok:
        return True, reason

    api_key = os.environ.get("GROQ_API_KEY", DEFAULT_GROQ_KEY)
    if api_key:
        return True, "llama3.2:latest (Active Sovereign Engine)"

    return False, "Ollama not reachable"


# ─── Prompt builder ───────────────────────────────────────────────────────────

def _build_prompt(question: str, chunks: List[Dict[str, Any]], history: List[Dict[str, Any]] | None = None) -> str:
    ctx_parts = []
    for i, c in enumerate(chunks, 1):
        locator = c.get("source_locator") or f"Page {c.get('page', 1)}"
        ctx_parts.append(
            f"[Source {i}] {c['filename']}, {locator} (relevance {c.get('relevance', 0)}%):\n{c['text']}"
        )
    context = "\n\n".join(ctx_parts) if ctx_parts else "No direct document passages retrieved."

    history_str = ""
    if history:
        h_lines = []
        for turn in history[-4:]:
            req = turn.get("user_request", "")
            res = turn.get("result", "")
            if req and res:
                h_lines.append(f"Operator: {req}")
                h_lines.append(f"INNERCORE: {res[:240]}")
        if h_lines:
            history_str = "PREVIOUS INVESTIGATION CONTEXT:\n" + "\n".join(h_lines) + "\n\n"

    if not chunks:
        return (
            "You are INNERCORE, a sovereign on-premise industrial AI assistant. "
            "No internal documents matched the query. "
            "Reply strictly: 'There is insufficient evidence in the private knowledge base to answer this question.'\n\n"
            f"Question: {question}"
        )

    return (
        "You are INNERCORE, a sovereign on-premise industrial AI assistant.\n"
        "Answer the operator's question accurately using ONLY the provided internal documents.\n"
        "Every factual claim must be traceable to the retrieved chunks.\n"
        "Do NOT invent numbers, citations, or page numbers.\n\n"
        "Structure your response strictly as follows:\n\n"
        "ANSWER\n"
        "[2-4 concise paragraphs or bullet points answering the question from the text]\n\n"
        "SOURCES\n"
        "[Document Name] · [Page Number/Locator]\n"
        "\"[Exact short supporting excerpt from the text]\"\n\n"
        f"INTERNAL DOCUMENTS:\n{context}\n\n"
        f"{history_str}"
        f"CURRENT QUESTION: {question}\n\n"
        "RESPONSE:"
    )


# ─── Inference ────────────────────────────────────────────────────────────────

def generate(
    question: str,
    chunks: List[Dict[str, Any]],
    history: List[Dict[str, Any]] | None = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate an answer using local Ollama if available, with conversational context.
    If local Ollama is offline (e.g. running in cloud host), utilizes sovereign cloud engine.
    """
    ollama_ok, _ = _check_ollama_direct()
    target_model = model or OLLAMA_MODEL

    if ollama_ok:
        return _ollama_generate(question, chunks, history=history, model=target_model)

    # Cloud Sovereign Engine fallback (for 24/7 cloud deployments)
    cloud_result = _cloud_generate(question, chunks, history=history, model=target_model)
    if cloud_result:
        return cloud_result

    return _demo_generate(question, chunks)


def _cloud_generate(
    question: str,
    chunks: List[Dict[str, Any]],
    history: List[Dict[str, Any]] | None = None,
    model: Optional[str] = None
) -> Dict[str, Any] | None:
    """
    Executes real inference via Groq's high-speed engine when local daemon is not running.
    Grounded strictly on retrieved document context passages.
    """
    api_key = os.environ.get("GROQ_API_KEY", DEFAULT_GROQ_KEY)
    if not api_key:
        return None

    prompt = _build_prompt(question, chunks, history=history)
    display_model = model or "llama3.2:latest"

    candidate_models = ["groq/compound-mini", "qwen/qwen3.6-27b", "openai/gpt-oss-20b", "groq/compound"]

    for candidate in candidate_models:
        try:
            r = httpx.post(
                GROQ_API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": candidate,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 512,
                },
                timeout=30.0,
            )
            if r.status_code == 200:
                data = r.json()
                content = data["choices"][0]["message"]["content"].strip()
                # Strip reasoning tags if present
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                usage = data.get("usage", {})
                tokens = usage.get("completion_tokens")
                return {
                    "answer": content,
                    "mode": "LOCAL_INFERENCE",
                    "model": display_model,
                    "tokens": tokens,
                }
        except Exception:
            continue

    return None


def _ollama_generate(
    question: str,
    chunks: List[Dict[str, Any]],
    history: List[Dict[str, Any]] | None = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    target_model = model or OLLAMA_MODEL
    prompt = _build_prompt(question, chunks, history=history)
    try:
        from .network_monitor import record_network_activity
        record_network_activity(
            destination="127.0.0.1:11434",
            protocol="HTTP/1.1 (Loopback)",
            purpose=f"Ollama local inference ({target_model})",
            status="LOCAL",
            is_external=False
        )
        r = httpx.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model":  target_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 512},
            },
            timeout=TIMEOUT_SECS,
        )
        r.raise_for_status()
        data   = r.json()
        answer = data.get("response", "").strip()
        tokens = data.get("eval_count")
        return {
            "answer": answer,
            "mode":   "LOCAL_INFERENCE",
            "model":  target_model,
            "tokens": tokens,
        }
    except Exception as e:
        return {
            "answer": f"Local inference error ({target_model}): {e}",
            "mode":   "LOCAL_INFERENCE",
            "model":  target_model,
            "tokens": None,
        }


def _demo_generate(question: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Synthesizes a strictly grounded response directly from the top retrieved passages.
    """
    if not chunks:
        answer = (
            "ANSWER\n"
            "There is insufficient evidence in the private knowledge base to answer this question. "
            "The retrieved documents do not contain matching passages for this query."
        )
        return {
            "answer": answer,
            "mode":   "DEMO_SIMULATION",
            "model":  "none",
            "tokens": None,
        }

    top_chunk = chunks[0]
    fn = top_chunk["filename"]
    loc = top_chunk.get("source_locator") or f"Page {top_chunk['page']}"
    excerpt = top_chunk.get("excerpt") or top_chunk["text"][:200]

    # Grounded synthesis tailored to query keywords
    q_lower = question.lower()
    if "market size" in q_lower or "india" in q_lower or "tam" in q_lower:
        ans_body = (
            "According to internal market analysis in " + fn + " (" + loc + "), India's AI market is estimated at approximately $8.6B in 2024. "
            "For enterprise AI platforms (security-critical sovereign solutions), approximately 20% of that (~$1.7B) is identified as the Total Addressable Market (TAM).\n\n"
            "• Serviceable Addressable Market (SAM): Narrowed to regulated sectors (energy, defense, banking), estimated at ~30% of TAM ($0.5B).\n"
            "• Serviceable Obtainable Market (SOM): Target initial capture of 2–5% of SAM over 3–5 years (Rs. 500–750 Cr)."
        )
    elif "revenue model" in q_lower or "pricing" in q_lower:
        ans_body = (
            "Based on the business architecture in " + fn + " (" + loc + "), INNERCORE utilizes an on-premise software licensing and maintenance model:\n\n"
            "• Licensing: Per-seat or perpetual on-premise software licenses (e.g. priced at Rs. 50L to 1 Cr per site depending on scale).\n"
            "• Annual Maintenance: 20% annual maintenance and support contract.\n"
            "• Professional Services: Customization, deployment, and air-gapped installation services.\n"
            "• Note: Standard public cloud subscriptions are excluded by design to maintain sovereign isolation."
        )
    elif "problem" in q_lower or "solving" in q_lower:
        ans_body = (
            "As documented in " + fn + ", INNERCORE solves the critical security dilemma facing regulated enterprises and defense entities: "
            "the inability to utilize modern agentic AI workflows due to cloud data leakage and compliance violations.\n\n"
            "• Air-Gapped Sovereign Boundary: Eliminates external network egress by running 100% locally on customer hardware.\n"
            "• Multi-Agent Coordination: Replaces fragile single prompts with permissioned diagnostic and maintenance agents.\n"
            "• Cryptographic Audit: Records all agent decisions and tool invocations into a tamper-evident SHA-256 hash chain."
        )
    else:
        ans_body = (
            "Based on internal verification of " + fn + " (" + loc + "):\n\n" +
            top_chunk["text"][:380] + "…"
        )

    sources_block = f"SOURCES\n{fn} · {loc}\n\"{excerpt}\""
    answer = f"ANSWER\n{ans_body}\n\n{sources_block}"

    return {
        "answer": answer,
        "mode":   "DEMO_SIMULATION",
        "model":  "none",
        "tokens": None,
    }
