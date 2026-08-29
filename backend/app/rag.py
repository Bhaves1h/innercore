"""
RAG pipeline — local, air-gapped.

PDF → PyMuPDF → semantic paragraph chunks + page metadata
    → local ONNX embeddings (all-MiniLM-L6-v2)
    → ChromaDB persistent vector store
    → hybrid semantic + keyword re-ranking
    → query-focused evidence excerpts with complete provenance.

No external network calls.
"""
from __future__ import annotations

import os
import re
import uuid
from typing import List, Dict, Any

# ChromaDB — persistent local vector store
import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
EMBED_MODEL = "all-MiniLM-L6-v2 (ONNX)"

# Singleton clients (initialised lazily)
_chroma_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None
_embed_fn: embedding_functions.DefaultEmbeddingFunction | None = None


def _get_embed_fn():
    global _embed_fn
    if _embed_fn is None:
        _embed_fn = embedding_functions.DefaultEmbeddingFunction()
    return _embed_fn


def _get_collection() -> chromadb.Collection:
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = _chroma_client.get_or_create_collection(
            name="innercore_knowledge",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ─── Text Cleaning & Normalization ───────────────────────────────────────────

def clean_text(t: str) -> str:
    """Normalize text, replace smart quotes and strip PDF markup artifacts."""
    if not t:
        return ""
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = t.replace("\u3010", "[").replace("\u3011", "]")
    t = t.replace("\u2018", "'").replace("\u2019", "'")
    t = t.replace("\u201c", '"').replace("\u201d", '"')
    t = t.replace("\u2013", "-").replace("\u2014", "-")
    t = t.replace("\u2022", "*").replace("\u2026", "...")
    t = t.replace("\u20b9", "Rs. ")
    t = t.replace("\u2265", ">=").replace("\u2264", "<=")
    # Remove PDF citation markers like [39†L10-L13] or ?39?L10-L13?
    t = re.sub(r'[\?\[]\d+[\?†]L\d+-L\d+[\?\]]', '', t)
    # Collapse duplicate spaces
    t = re.sub(r'[ \t]+', ' ', t)
    return t.strip()


# ─── Query-Focused Excerpt Extractor ─────────────────────────────────────────

def extract_query_excerpt(query: str, chunk_text: str, max_len: int = 240) -> str:
    """
    Extract the most relevant sentence or window in chunk_text matching the user query.
    Ensures evidence cards show the exact supporting passage.
    """
    cleaned = clean_text(chunk_text)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?\n])\s+', cleaned) if s.strip()]
    if not sentences:
        return cleaned[:max_len] + ("…" if len(cleaned) > max_len else "")

    stopwords = {"what", "is", "the", "of", "in", "and", "a", "to", "for", "are", "on", "how", "why", "it", "with", "by", "an", "at"}
    q_words = set(re.findall(r'\w+', query.lower())) - stopwords

    scored = []
    for idx, s in enumerate(sentences):
        s_words = set(re.findall(r'\w+', s.lower()))
        overlap = len(q_words & s_words)
        scored.append((overlap, idx, s))

    scored.sort(key=lambda x: (-x[0], x[1]))
    best_overlap, best_idx, best_sent = scored[0]

    if best_overlap > 0:
        res = best_sent
        # If sentence is short, append next sentence for natural context
        if len(res) < 140 and best_idx + 1 < len(sentences):
            res += " " + sentences[best_idx + 1]
        if len(res) > max_len:
            res = res[:max_len].rsplit(' ', 1)[0] + "…"
        return res

    return cleaned[:max_len] + ("…" if len(cleaned) > max_len else "")


# ─── Semantic Paragraph Chunking ─────────────────────────────────────────────

def _chunk_text(
    text: str,
    page: int,
    doc_id: str,
    filename: str,
    file_type: str = "PDF",
    source_locator: str | None = None
) -> List[Dict[str, Any]]:
    """
    Split text into coherent semantic units (paragraph and sentence boundaries, ~350–550 chars).
    """
    chunks = []
    locator = source_locator or f"Page {page}"
    cleaned = clean_text(text)
    if not cleaned:
        return chunks

    raw_paragraphs = [p.strip() for p in re.split(r'\n\s*\n', cleaned) if p.strip()]
    if not raw_paragraphs:
        raw_paragraphs = [cleaned]

    c_idx = 0
    curr_chunk = ""

    for p in raw_paragraphs:
        # If a single paragraph is large (> 550 chars), split by sentences
        if len(p) > 550:
            sentences = re.split(r'(?<=[.!?])\s+', p)
            sub_curr = ""
            for s in sentences:
                if len(sub_curr) + len(s) > 450:
                    if sub_curr.strip():
                        chunks.append({
                            "id":             f"{doc_id}-p{page}-c{c_idx}",
                            "text":           sub_curr.strip(),
                            "doc_id":         doc_id,
                            "filename":       filename,
                            "file_type":      file_type,
                            "page":           page,
                            "source_locator": locator,
                            "chunk_idx":      c_idx,
                        })
                        c_idx += 1
                    sub_curr = s + " "
                else:
                    sub_curr += s + " "
            if sub_curr.strip():
                chunks.append({
                    "id":             f"{doc_id}-p{page}-c{c_idx}",
                    "text":           sub_curr.strip(),
                    "doc_id":         doc_id,
                    "filename":       filename,
                    "file_type":      file_type,
                    "page":           page,
                    "source_locator": locator,
                    "chunk_idx":      c_idx,
                })
                c_idx += 1
        else:
            if len(curr_chunk) + len(p) > 450:
                if curr_chunk.strip():
                    chunks.append({
                        "id":             f"{doc_id}-p{page}-c{c_idx}",
                        "text":           curr_chunk.strip(),
                        "doc_id":         doc_id,
                        "filename":       filename,
                        "file_type":      file_type,
                        "page":           page,
                        "source_locator": locator,
                        "chunk_idx":      c_idx,
                    })
                    c_idx += 1
                curr_chunk = p + "\n\n"
            else:
                curr_chunk += p + "\n\n"

    if curr_chunk.strip():
        chunks.append({
            "id":             f"{doc_id}-p{page}-c{c_idx}",
            "text":           curr_chunk.strip(),
            "doc_id":         doc_id,
            "filename":       filename,
            "file_type":      file_type,
            "page":           page,
            "source_locator": locator,
            "chunk_idx":      c_idx,
        })

    return chunks


# ─── Document Processing (PDF, DOCX, TXT, MD, CSV) ───────────────────────────

def _extract_docx(file_bytes: bytes) -> List[tuple[int, str, str]]:
    import io
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = []
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt:
                paragraphs.append(txt)
        for t in doc.tables:
            for row in t.rows:
                row_txt = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_txt:
                    paragraphs.append(row_txt)
        full_text = "\n\n".join(paragraphs)
    except Exception:
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml_content = z.read("word/document.xml")
        tree = ET.fromstring(xml_content)
        texts = [node.text for node in tree.iter() if node.text]
        full_text = " ".join(texts)

    sections = []
    blocks = [b.strip() for b in full_text.split("\n\n") if b.strip()]
    if not blocks:
        blocks = [full_text] if full_text.strip() else []

    curr_text = ""
    sec_idx = 1
    for b in blocks:
        if len(curr_text) + len(b) > 1500:
            if curr_text.strip():
                sections.append((sec_idx, f"Section {sec_idx}", curr_text.strip()))
                sec_idx += 1
                curr_text = b + "\n\n"
        else:
            curr_text += b + "\n\n"
    if curr_text.strip():
        sections.append((sec_idx, f"Section {sec_idx}", curr_text.strip()))
    return sections


def _extract_csv(file_bytes: bytes) -> List[tuple[int, str, str]]:
    import csv
    import io
    text_content = file_bytes.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text_content))
    rows = list(reader)
    if not rows:
        return []

    headers = rows[0]
    data_rows = rows[1:] if len(rows) > 1 else rows

    sections = []
    group_size = 12
    for i in range(0, len(data_rows), group_size):
        chunk_rows = data_rows[i:i + group_size]
        sec_num = (i // group_size) + 1
        locator = f"Rows {i + 1}-{min(i + group_size, len(data_rows))}"
        formatted = []
        for r_idx, r in enumerate(chunk_rows, start=i + 1):
            if headers and len(headers) == len(r):
                row_str = f"Row {r_idx}: " + ", ".join(f"{h}={v}" for h, v in zip(headers, r) if v)
            else:
                row_str = f"Row {r_idx}: " + ", ".join(r)
            formatted.append(row_str)
        sections.append((sec_num, locator, "\n".join(formatted)))
    return sections


def _extract_plain_text(file_bytes: bytes, filename: str) -> List[tuple[int, str, str]]:
    text = file_bytes.decode("utf-8", errors="replace")
    if filename.lower().endswith((".md", ".markdown")) and ("\n# " in text or text.startswith("# ")):
        parts = re.split(r"(?=\n#+ )", "\n" + text)
        sections = []
        sec_idx = 1
        for p in parts:
            p_str = p.strip()
            if p_str:
                first_line = p_str.split("\n")[0].replace("#", "").strip()
                locator = f"Section {sec_idx}: {first_line[:30]}" if first_line else f"Section {sec_idx}"
                sections.append((sec_idx, locator, p_str))
                sec_idx += 1
        if sections:
            return sections

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text] if text.strip() else []

    sections = []
    curr = ""
    sec_idx = 1
    for p in paragraphs:
        if len(curr) + len(p) > 1500:
            if curr.strip():
                sections.append((sec_idx, f"Section {sec_idx}", curr.strip()))
                sec_idx += 1
                curr = p + "\n\n"
        else:
            curr += p + "\n\n"
    if curr.strip():
        sections.append((sec_idx, f"Section {sec_idx}", curr.strip()))
    return sections


def process_document(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Process PDF, DOCX, TXT, MD, CSV into semantic chunks with provenance and index into ChromaDB.
    """
    doc_id = str(uuid.uuid4())
    ext = os.path.splitext(filename)[1].lower()
    all_chunks: List[Dict[str, Any]] = []
    page_count = 1

    print(f"[RAG] Processing '{filename}' (format: {ext})...")

    if ext == ".pdf":
        import pymupdf
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        page_count = max(1, len(doc))
        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text")
            chunks = _chunk_text(text, page_num + 1, doc_id, filename, file_type="PDF", source_locator=f"Page {page_num + 1}")
            all_chunks.extend(chunks)
        doc.close()

    elif ext in [".docx", ".doc"]:
        sections = _extract_docx(file_bytes)
        page_count = max(1, len(sections))
        for sec_num, locator, sec_text in sections:
            chunks = _chunk_text(sec_text, sec_num, doc_id, filename, file_type="DOCX", source_locator=locator)
            all_chunks.extend(chunks)

    elif ext in [".csv", ".tsv"]:
        sections = _extract_csv(file_bytes)
        page_count = max(1, len(sections))
        for sec_num, locator, sec_text in sections:
            chunks = _chunk_text(sec_text, sec_num, doc_id, filename, file_type="CSV", source_locator=locator)
            all_chunks.extend(chunks)

    else:
        file_type = "MD" if ext in [".md", ".markdown"] else "TXT"
        sections = _extract_plain_text(file_bytes, filename)
        page_count = max(1, len(sections))
        for sec_num, locator, sec_text in sections:
            chunks = _chunk_text(sec_text, sec_num, doc_id, filename, file_type=file_type, source_locator=locator)
            all_chunks.extend(chunks)

    print(f"[RAG] Extracted {len(all_chunks)} semantic chunks across {page_count} units from {filename}")

    if not all_chunks:
        raise ValueError(f"No extractable text found in '{filename}'.")

    collection = _get_collection()
    try:
        collection.delete(where={"filename": filename})
    except Exception:
        pass

    embed_fn = _get_embed_fn()
    texts = [c["text"] for c in all_chunks]
    print(f"[RAG] Generating embeddings for {len(texts)} chunks...")
    embeddings = embed_fn(texts)
    print(f"[RAG] Generated {len(embeddings)} embeddings. Indexing in ChromaDB...")

    collection.add(
        ids        = [c["id"] for c in all_chunks],
        embeddings = embeddings,
        documents  = texts,
        metadatas  = [{
            "doc_id":         c["doc_id"],
            "filename":       c["filename"],
            "file_type":      c.get("file_type", "DOC"),
            "page":           c["page"],
            "source_locator": c.get("source_locator", f"Page {c['page']}"),
            "chunk_idx":      c["chunk_idx"],
        } for c in all_chunks],
    )
    print(f"[RAG] Successfully indexed {filename} into ChromaDB!")

    return {
        "doc_id":      doc_id,
        "filename":    filename,
        "file_type":   all_chunks[0].get("file_type", "DOC"),
        "page_count":  page_count,
        "chunk_count": len(all_chunks),
        "status":      "INDEXED",
    }


def process_pdf(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    return process_document(file_bytes, filename)


# ─── Hybrid Semantic + Lexical Retrieval ──────────────────────────────────────

def _auto_index_default_document():
    try:
        pdf_candidates = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Executive Summary.pdf")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Executive Summary.pdf")),
            os.path.abspath(os.path.join(os.getcwd(), "Executive Summary.pdf")),
            os.path.abspath(os.path.join(os.getcwd(), "backend", "Executive Summary.pdf")),
        ]
        for p in pdf_candidates:
            if os.path.exists(p) and os.path.isfile(p):
                with open(p, "rb") as f:
                    pdf_bytes = f.read()
                print(f"[RAG] Auto-indexing default document: {p}")
                process_document(pdf_bytes, "Executive Summary.pdf")
                break
    except Exception as e:
        print(f"[RAG] Auto-indexing default document notice: {e}")


def search_knowledge(query: str, n_results: int = 5, doc_filter: str | None = None) -> List[Dict[str, Any]]:
    """
    Hybrid semantic + lexical search across the knowledge base.
    Ranks chunks by semantic cosine similarity + keyword overlap boost.
    Attaches query-focused excerpt to each retrieved evidence chunk.
    """
    try:
        collection = _get_collection()
        count = collection.count()
        if count == 0:
            _auto_index_default_document()
            count = collection.count()
            if count == 0:
                return []

        fetch_n = min(max(n_results * 4, 15), count)
        query_emb = _get_embed_fn()([query])

        query_kwargs: Dict[str, Any] = {
            "query_embeddings": query_emb,
            "n_results": fetch_n,
            "include": ["documents", "metadatas", "distances"],
        }
        if doc_filter and doc_filter not in ["ALL", "ALL DOCUMENTS"]:
            query_kwargs["where"] = {"filename": doc_filter}

        try:
            results = collection.query(**query_kwargs)
        except Exception:
            query_kwargs.pop("where", None)
            results = collection.query(**query_kwargs)

        if not results or not results["documents"] or not results["documents"][0]:
            return []

        docs      = results["documents"][0]
        metas     = results["metadatas"][0]
        distances = results["distances"][0]

        stopwords = {"what", "is", "the", "of", "in", "and", "a", "to", "for", "are", "on", "how", "why", "it", "with", "by", "an", "at", "who"}
        q_tokens = [w.lower() for w in re.findall(r'\w+', query) if w.lower() not in stopwords]

        candidate_chunks = []
        seen_keys = set()

        for text, meta, dist in zip(docs, metas, distances):
            fn       = meta.get("filename", "Unknown")
            pg       = meta.get("page", 1)
            locator  = meta.get("source_locator") or f"Page {pg}"
            cidx     = meta.get("chunk_idx", 0)
            ftype    = meta.get("file_type", "DOC")

            stable_key = f"{fn}::p{pg}::c{cidx}"
            if stable_key in seen_keys:
                continue
            seen_keys.add(stable_key)

            # Base semantic cosine similarity: range 0.0 to 1.0
            cosine_sim = max(0.0, 1.0 - (dist / 2.0))

            # Lexical keyword match ratio
            t_lower = text.lower()
            matched_tokens = sum(1 for tok in q_tokens if tok in t_lower)
            lexical_ratio = (matched_tokens / len(q_tokens)) if q_tokens else 0.0

            # Composite score: 65% dense semantic + 35% exact term boost
            composite_score = (cosine_sim * 0.65) + (lexical_ratio * 0.35)
            relevance_pct = round(min(1.0, composite_score) * 100, 1)

            # Extract focused supporting excerpt
            excerpt = extract_query_excerpt(query, text, max_len=240)

            candidate_chunks.append({
                "text":           clean_text(text),
                "excerpt":        excerpt,
                "filename":       fn,
                "file_type":      ftype,
                "page":           pg,
                "source_locator": locator,
                "relevance":      relevance_pct,
                "doc_id":         meta.get("doc_id", ""),
                "chunk_idx":      cidx,
                "matched_tokens": matched_tokens,
            })

        # Sort candidates by composite relevance descending
        candidate_chunks.sort(key=lambda x: -x["relevance"])

        # Filter out irrelevant noise (relevance must be at least 32%)
        filtered = [c for c in candidate_chunks if c["relevance"] >= 32.0]
        return filtered[:n_results]

    except Exception as e:
        print(f"[RAG] Search knowledge error: {e}")
        return []


# ─── Document list & Page viewer ──────────────────────────────────────────────

def list_documents() -> List[Dict[str, Any]]:
    collection = _get_collection()
    if collection.count() == 0:
        return []

    result = collection.get(include=["metadatas"])
    seen: Dict[str, Dict[str, Any]] = {}
    for meta in result.get("metadatas", []):
        fn = meta.get("filename", "Unknown")
        if fn not in seen:
            seen[fn] = {
                "doc_id":     meta.get("doc_id", ""),
                "filename":   fn,
                "file_type":  meta.get("file_type", "DOC"),
                "pages":      set(),
                "chunks":     0,
                "status":     "INDEXED",
            }
        seen[fn]["pages"].add(meta.get("page", 1))
        seen[fn]["chunks"] += 1

    docs = []
    for v in seen.values():
        docs.append({
            "doc_id":      v["doc_id"],
            "filename":    v["filename"],
            "file_type":   v.get("file_type", "DOC"),
            "page_count":  len(v["pages"]),
            "chunk_count": v["chunks"],
            "status":      v["status"],
            "boundary":    "LOCAL AIR-GAPPED",
        })
    return docs


def get_document_details(filename: str) -> Dict[str, Any]:
    collection = _get_collection()
    if collection.count() == 0:
        return {"filename": filename, "doc_id": "", "page_count": 0, "chunk_count": 0, "status": "NOT_FOUND", "boundary": "LOCAL AIR-GAPPED", "excerpts": []}

    total_res = collection.get(where={"filename": filename}, include=["metadatas", "documents"])
    docs  = total_res.get("documents", [])
    metas = total_res.get("metadatas", [])

    if not docs:
        return {"filename": filename, "doc_id": "", "page_count": 0, "chunk_count": 0, "status": "NOT_FOUND", "boundary": "LOCAL AIR-GAPPED", "excerpts": []}

    all_pages = set()
    excerpts  = []
    doc_id    = ""
    for d, m in zip(docs, metas):
        doc_id = m.get("doc_id", doc_id)
        pg     = m.get("page", 1)
        all_pages.add(pg)
        excerpts.append({
            "page":      pg,
            "chunk_idx": m.get("chunk_idx", 0),
            "text":      clean_text(d),
        })

    excerpts.sort(key=lambda x: (x["page"], x["chunk_idx"]))

    return {
        "filename":    filename,
        "doc_id":      doc_id,
        "page_count":  len(all_pages),
        "chunk_count": len(docs),
        "status":      "INDEXED",
        "boundary":    "LOCAL AIR-GAPPED",
        "excerpts":    excerpts[:6],
    }


def get_document_page(filename: str, page: int = 1) -> Dict[str, Any]:
    """
    Retrieve full text and chunks for a specific page of an indexed document.
    """
    collection = _get_collection()
    if collection.count() == 0:
        return {"filename": filename, "page": page, "total_pages": 1, "page_text": "", "chunks": []}

    total_res = collection.get(where={"filename": filename}, include=["metadatas", "documents"])
    docs  = total_res.get("documents", [])
    metas = total_res.get("metadatas", [])

    if not docs:
        return {"filename": filename, "page": page, "total_pages": 1, "page_text": "", "chunks": []}

    all_pages = set()
    page_chunks = []
    file_type = "DOC"
    source_locator = f"Page {page}"

    for d, m in zip(docs, metas):
        pg = m.get("page", 1)
        all_pages.add(pg)
        if m.get("file_type"):
            file_type = m.get("file_type")
        if pg == page:
            source_locator = m.get("source_locator") or f"Page {pg}"
            page_chunks.append({
                "chunk_idx":      m.get("chunk_idx", 0),
                "text":           clean_text(d),
                "source_locator": source_locator,
                "file_type":      file_type,
            })

    total_pages = max(1, len(all_pages))
    page_chunks.sort(key=lambda x: x["chunk_idx"])
    full_page_text = "\n\n".join(c["text"] for c in page_chunks)

    return {
        "filename":       filename,
        "page":           page,
        "total_pages":    total_pages,
        "file_type":      file_type,
        "source_locator": source_locator,
        "page_text":      full_page_text,
        "chunks":         page_chunks,
    }
