#!/usr/bin/env python3
"""
HUCE-KMS — Offline RAG Pipeline Evaluation & Inspection Tool.

Executes each RAG pipeline stage step-by-step on a local document and dumps
structured JSON artifacts for inspection, tuning, and prompt evaluation.

Usage:
    # Run Stages 1-3 on default or sample file
    uv run python scripts/eval_pipeline.py

    # Run on a specific PDF with a custom query
    uv run python scripts/eval_pipeline.py --file data/samples/quy_che_43.pdf --query "Học phần là gì?"

    # Include Step 4 (LLM Answer Synthesis via Gemini)
    uv run python scripts/eval_pipeline.py --file data/samples/quy_che_43.pdf --query "Khối lượng đào tạo 5 năm tối thiểu bao nhiêu tín chỉ?" --synthesis
"""

import argparse
import json
import logging
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# Ensure apps/backend/src is in pythonpath
current_dir = Path(__file__).resolve().parent
backend_root = current_dir.parent
src_dir = backend_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from api.core.config import settings
from api.services.rag.chunker import TextChunker
from api.services.rag.cleaner import TextCleaner
from api.services.rag.parser import DocumentParser
from api.services.rag.service import HUCE_SYSTEM_INSTRUCTION

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass


def print_banner(title: str) -> None:
    sep = "=" * 65
    print(f"\n{sep}\n  {title}\n{sep}")


def print_step_header(step_num: int, title: str) -> None:
    print(f"\n[STEP {step_num}] {title}")
    print("-" * 65)


def safe_save_json(output_path: Path, data: Any) -> Path:
    """Save data to JSON, falling back to tempdir if permission is restricted."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path
    except (PermissionError, OSError):
        fallback_dir = Path(tempfile.gettempdir()) / "huce_kms_rag_eval"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_path = fallback_dir / output_path.name
        with open(fallback_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  (Note: Output written to fallback path: {fallback_path})")
        return fallback_path


def compute_cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Calculate cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def compute_lexical_overlap(query: str, text: str) -> float:
    """Fallback lexical similarity when embedding API is offline."""
    q_words = set(query.lower().split())
    if not q_words:
        return 0.0
    t_words = set(text.lower().split())
    intersection = q_words & t_words
    return len(intersection) / len(q_words)


def run_pipeline(
    file_path: Path,
    query: str,
    strategy: str = "legal_structural",
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    top_k: int = 3,
    threshold: float = 0.35,
    output_dir: Path = backend_root / "output" / "rag_eval",
    do_synthesis: bool = False,
    is_offline: bool = False,
) -> None:
    print_banner(f"HUCE-KMS RAG PIPELINE INSPECTION\n  Target File: {file_path.name}\n  Strategy:    {strategy}")

    if not file_path.exists():
        print(f"[Error] File not found: {file_path}")
        sys.exit(1)

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # -------------------------------------------------------------------------
    # STEP 1: PARSE & CLEAN
    # -------------------------------------------------------------------------
    print_step_header(1, "EXTRACT & CLEAN DOCUMENT")
    raw_pages = DocumentParser.parse(file_bytes, file_name=file_path.name)
    cleaned_pages = TextCleaner.clean_pages(raw_pages)

    total_raw_chars = sum(len(str(p.get("text", ""))) for p in raw_pages)
    total_cleaned_chars = sum(len(p.get("cleaned_text", "")) for p in cleaned_pages)
    noise_count = sum(len(p.get("removed_noise", [])) for p in cleaned_pages)

    step1_payload = {
        "file_name": file_path.name,
        "total_pages": len(cleaned_pages),
        "total_raw_chars": total_raw_chars,
        "total_cleaned_chars": total_cleaned_chars,
        "characters_filtered": total_raw_chars - total_cleaned_chars,
        "total_noise_lines_removed": noise_count,
        "pages": [
            {
                "page_number": p["page_number"],
                "raw_text": p["raw_text"],
                "cleaned_text": p["cleaned_text"],
                "removed_noise": p["removed_noise"],
                "char_count": p["char_count"],
            }
            for p in cleaned_pages
        ],
    }

    step1_file = safe_save_json(output_dir / "step1_extract_clean.json", step1_payload)
    print(f"  Pages Extracted:     {len(cleaned_pages)}")
    print(f"  Raw Characters:      {total_raw_chars:,}")
    print(f"  Cleaned Characters:  {total_cleaned_chars:,} (Reduced: {total_raw_chars - total_cleaned_chars:,})")
    print(f"  Noise Lines Removed: {noise_count}")
    print(f"  Artifact Saved:      {step1_file}")

    # -------------------------------------------------------------------------
    # STEP 2: CHUNKING & CONTEXTUAL BREADCRUMBS
    # -------------------------------------------------------------------------
    print_step_header(2, f"CHUNK WITH STRATEGY: '{strategy}'")
    doc_title = file_path.stem.replace("_", " ").title()

    chunks_raw = TextChunker.chunk_with_strategy(
        pages=[{"page_number": p["page_number"], "text": p["cleaned_text"]} for p in cleaned_pages],
        strategy=strategy,
        document_title=doc_title,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    total_tokens = sum(c.get("token_count", 0) for c in chunks_raw)
    avg_tokens = round(total_tokens / len(chunks_raw), 1) if chunks_raw else 0.0

    step2_payload = {
        "strategy": strategy,
        "document_title": doc_title,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "total_chunks": len(chunks_raw),
        "total_tokens": total_tokens,
        "avg_tokens": avg_tokens,
        "chunks": chunks_raw,
    }

    step2_file = safe_save_json(output_dir / "step2_chunks.json", step2_payload)
    print(f"  Total Chunks:        {len(chunks_raw)}")
    print(f"  Average Tokens:      {avg_tokens} tokens/chunk")
    print(f"  Artifact Saved:      {step2_file}")

    print("\n  Sample Chunks Preview:")
    for idx, c in enumerate(chunks_raw[:4]):
        heading = c.get("heading_path") or "(Root)"
        tokens = c.get("token_count", 0)
        excerpt = c.get("content", "").replace("\n", " ")[:90]
        print(f"    [{idx}] P.{c.get('page_number')} | {tokens:3d} toks | {heading[:40]}")
        print(f"        \"{excerpt}...\"")

    # -------------------------------------------------------------------------
    # STEP 3: EMBEDDING & RETRIEVAL RANKING
    # -------------------------------------------------------------------------
    print_step_header(3, f"RETRIEVAL & COSINE RANKING\n  Query: \"{query}\"")

    scored_chunks: list[dict[str, Any]] = []
    used_model = "dense_gemini"

    if settings.GEMINI_API_KEY and not is_offline:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            cfg = types.EmbedContentConfig(output_dimensionality=settings.VECTOR_DIMENSION)

            # Embed query
            res_q = client.models.embed_content(
                model=settings.EMBEDDING_MODEL_NAME,
                contents=query,
                config=cfg,
            )
            query_vector = res_q.embedding.values

            # Embed chunks
            chunk_texts = [c["content"] for c in chunks_raw]
            res_c = client.models.embed_content(
                model=settings.EMBEDDING_MODEL_NAME,
                contents=chunk_texts,
                config=cfg,
            )
            chunk_vectors = [e.values for e in res_c.embeddings]

            for c, vec in zip(chunks_raw, chunk_vectors):
                score = round(compute_cosine_similarity(query_vector, vec), 4)
                scored_chunks.append({**c, "score": score})
        except Exception as e:
            print(f"  (Notice: Gemini Embedding call failed or timed out: {e}. Using lexical token overlap.)")
            used_model = "lexical_overlap"
            for c in chunks_raw:
                score = round(compute_lexical_overlap(query, c["content"]), 4)
                scored_chunks.append({**c, "score": score})
    else:
        print("  (Notice: Offline mode. Using lexical token similarity for evaluation.)")
        used_model = "lexical_overlap"
        for c in chunks_raw:
            score = round(compute_lexical_overlap(query, c["content"]), 4)
            scored_chunks.append({**c, "score": score})

    # Sort descending by score
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    top_candidates = [c for c in scored_chunks if c["score"] >= threshold][:top_k]

    # Assemble Institutional Prompt
    context_blocks = []
    for rank, c in enumerate(top_candidates, 1):
        context_blocks.append(
            f"[Trích đoạn {rank}] Trang {c.get('page_number')} | {c.get('heading_path')}\n{c.get('content')}"
        )
    context_str = "\n\n---\n\n".join(context_blocks) if context_blocks else "(Không tìm thấy trích đoạn phù hợp)"

    assembled_prompt = {
        "system_instruction": HUCE_SYSTEM_INSTRUCTION,
        "user_query": query,
        "assembled_context": context_str,
        "full_prompt_text": f"Dựa vào các điều khoản quy định sau của HUCE:\n\n{context_str}\n\nCâu hỏi: {query}",
    }

    step3_payload = {
        "query": query,
        "scoring_model": used_model,
        "top_k": top_k,
        "similarity_threshold": threshold,
        "total_chunks_evaluated": len(scored_chunks),
        "matched_chunks_count": len(top_candidates),
        "retrieved_chunks": [
            {
                "rank": rank,
                "chunk_index": c.get("chunk_index"),
                "score": c.get("score"),
                "page_number": c.get("page_number"),
                "heading_path": c.get("heading_path"),
                "content": c.get("content"),
            }
            for rank, c in enumerate(top_candidates, 1)
        ],
        "assembled_prompt": assembled_prompt,
    }

    step3_file = safe_save_json(output_dir / "step3_retrieval.json", step3_payload)
    print(f"  Scoring Model:       {used_model}")
    print(f"  Threshold:           >= {threshold}")
    print(f"  Retrieved Chunks:    {len(top_candidates)} / {top_k} requested")
    print(f"  Artifact Saved:      {step3_file}")

    print("\n  Top Ranked Chunks:")
    if top_candidates:
        for rank, c in enumerate(top_candidates, 1):
            heading = c.get("heading_path") or "(Root)"
            excerpt = c.get("content", "").replace("\n", " ")[:110]
            print(f"    #{rank} Score: {c['score']:.4f} | P.{c.get('page_number')} | {heading[:40]}")
            print(f"        \"{excerpt}...\"")
    else:
        print("    (No chunk passed the similarity threshold)")

    # -------------------------------------------------------------------------
    # STEP 4: GENERATION (SYNTHESIS)
    # -------------------------------------------------------------------------
    if do_synthesis:
        print_step_header(4, "LLM ANSWER SYNTHESIS (GEMINI)")
        if not settings.GEMINI_API_KEY:
            print("  [Skip] GEMINI_API_KEY not configured. Cannot run Step 4.")
        elif not top_candidates:
            print("  [Skip] No relevant context retrieved to answer query.")
        else:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                response = client.models.generate_content(
                    model=settings.LLM_MODEL,
                    contents=assembled_prompt["full_prompt_text"],
                    config=types.GenerateContentConfig(
                        system_instruction=HUCE_SYSTEM_INSTRUCTION,
                        temperature=0.3,
                    ),
                )
                answer_text = response.text.strip() if response.text else "(No answer generated)"

                step4_payload = {
                    "query": query,
                    "llm_model": settings.LLM_MODEL,
                    "answer": answer_text,
                    "sources": [
                        {
                            "rank": rank,
                            "page": c.get("page_number"),
                            "heading": c.get("heading_path"),
                            "score": c.get("score"),
                        }
                        for rank, c in enumerate(top_candidates, 1)
                    ],
                }

                step4_file = safe_save_json(output_dir / "step4_synthesis.json", step4_payload)
                print(f"  Model:               {settings.LLM_MODEL}")
                print(f"  Artifact Saved:      {step4_file}")
                print(f"\n  Final Answer:\n  {answer_text}\n")
            except Exception as e:
                print(f"  [Error] LLM generation failed: {e}")

    print_banner("EVALUATION COMPLETE — JSON ARTIFACTS READY IN OUTPUT DIRECTORY")


def main() -> None:
    parser = argparse.ArgumentParser(description="HUCE-KMS Offline RAG Pipeline Evaluation Tool")
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default=None,
        help="Path to PDF, TXT, or MD document. Default: searches data/samples/",
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default="Khối lượng chương trình đào tạo đại học 5 năm tối thiểu là bao nhiêu tín chỉ?",
        help="Evaluation question for Step 3 Retrieval",
    )
    parser.add_argument(
        "--strategy",
        "-s",
        type=str,
        choices=["legal_structural", "recursive"],
        default="legal_structural",
        help="Chunking strategy (default: legal_structural)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=800,
        help="Max chunk size in characters (default: 800)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=150,
        help="Overlap characters for recursive fallback (default: 150)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of chunks to retrieve (default: 3)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.35,
        help="Cosine similarity threshold (default: 0.35)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=str(backend_root / "output" / "rag_eval"),
        help="Directory to save JSON output files",
    )
    parser.add_argument(
        "--synthesis",
        action="store_true",
        help="Call Gemini LLM to synthesize final answer (Step 4)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run without calling external Gemini API (pure local lexical evaluation)",
    )

    args = parser.parse_args()

    # Determine input file
    target_file: Path | None = None
    if args.file:
        target_file = Path(args.file).resolve()
    else:
        sample_dir = backend_root / "data" / "samples"
        pdf_candidates = [f for f in sample_dir.glob("*.pdf") if f.name != "README.md"]
        other_candidates = [
            f for f in (list(sample_dir.glob("*.txt")) + list(sample_dir.glob("*.md")))
            if f.name != "README.md" and not f.name.startswith("sample_")
        ]
        candidates = pdf_candidates + other_candidates
        if candidates:
            target_file = candidates[0]
        else:
            print("[Error] No sample documents found in data/samples/. Please specify --file <path>.")
            sys.exit(1)

    run_pipeline(
        file_path=target_file,
        query=args.query,
        strategy=args.strategy,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        top_k=args.top_k,
        threshold=args.threshold,
        output_dir=Path(args.output_dir),
        do_synthesis=args.synthesis,
        is_offline=args.offline,
    )


if __name__ == "__main__":
    main()
