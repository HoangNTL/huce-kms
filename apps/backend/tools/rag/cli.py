#!/usr/bin/env python3
"""
HUCE-KMS — RAG Inspection & Testing CLI Tool (tools/rag/cli.py)

Command-line developer utility to inspect, test, and tune RAG pipeline stages:
  1. extract  : Inspect raw document extraction and noise cleaning.
  2. chunk    : Test chunking strategies ('legal_structural' vs 'recursive') and token analytics.
  3. retrieve : Inspect semantic vector retrieval and prompt assembly against Qdrant.
  4. eval     : Run the full end-to-end evaluation pipeline on a file and query.

Usage:
  # Step 1: Extraction & Cleaning Preview
  uv run python tools/rag/cli.py extract --file data/sample.pdf

  # Step 2: Chunking Strategy Preview
  uv run python tools/rag/cli.py chunk --file data/sample.pdf --strategy legal_structural
  uv run python tools/rag/cli.py chunk --text "CHƯƠNG I: QUY ĐỊNH CHUNG\n\nĐiều 1..." --strategy legal_structural

  # Step 3: Retrieval & Prompt Assembly Preview
  uv run python tools/rag/cli.py retrieve --query "Học phần là gì?" --top-k 3

  # Step 4: Full Pipeline Evaluation
  uv run python tools/rag/cli.py eval --file data/sample.pdf --query "Quy chế đào tạo là gì?"
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

# Ensure apps/backend/src is in pythonpath
current_dir = Path(__file__).resolve().parent
backend_root = current_dir.parent.parent
src_dir = backend_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from api.core.config import settings
from api.schemas.rag_preview import (
    ChunkPreviewResponse,
    ExtractPreviewResponse,
    RetrievalPreviewResponse,
)
from api.services.ai.managers.embedding_manager import EmbeddingManager
from api.services.ai.managers.generation_manager import GenerationManager
from api.services.rag.chunker import TextChunker
from api.services.rag.cleaner import TextCleaner
from api.services.rag.parser import DocumentParser
from api.services.rag.service import RAGService
from api.services.rag.vector_store import QdrantVectorStore

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def print_banner(title: str) -> None:
    sep = "=" * 70
    print(f"\n{sep}\n  {title}\n{sep}")


def print_section(title: str) -> None:
    print(f"\n--- {title} " + "-" * max(5, 65 - len(title)))


def safe_save_json(output_path: Path, data: Any) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[Artifact Saved] -> {output_path.resolve()}")


# -----------------------------------------------------------------------------
# Command 1: EXTRACT (Inspection of Parsing & Cleaning)
# -----------------------------------------------------------------------------
def handle_extract(args: argparse.Namespace) -> None:
    file_path: Path = args.file
    if not file_path.exists():
        print(f"[Error] File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    print_banner(f"RAG PREVIEW: EXTRACTION & TEXT SANITATION\n  File: {file_path.name}")

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    print("[1/2] Parsing document...")
    preview: ExtractPreviewResponse = TextCleaner.extract_and_clean_preview(
        file_bytes=file_bytes,
        file_name=file_path.name,
    )

    print("[2/2] Sanitation analysis complete.")
    print_section("Extraction Summary")
    print(f"  • Total Pages Parsed    : {preview.total_pages}")
    print(f"  • Raw Character Count   : {preview.total_raw_chars:,}")
    print(f"  • Cleaned Character Count: {preview.total_cleaned_chars:,}")
    chars_removed = preview.total_raw_chars - preview.total_cleaned_chars
    reduction_pct = (chars_removed / preview.total_raw_chars * 100) if preview.total_raw_chars else 0
    print(f"  • Characters Stripped   : {chars_removed:,} ({reduction_pct:.1f}%)")

    total_noise_lines = sum(len(p.removed_noise) for p in preview.pages)
    print(f"  • Noise Lines Removed   : {total_noise_lines}")

    print_section("Per-Page Breakdown Preview")
    for page in preview.pages[: args.max_pages]:
        print(f"\n  [Page {page.page_number}] ({page.char_count} chars)")
        if page.removed_noise:
            print("    Stripped Headers/Footers:")
            for n in page.removed_noise[:3]:
                print(f"      - \"{n}\"")
            if len(page.removed_noise) > 3:
                print(f"      ... and {len(page.removed_noise) - 3} more lines")

        snippet = page.cleaned_text.replace("\n", " ").strip()[:140]
        print(f"    Cleaned Content Excerpt:\n      \"{snippet}...\"")

    if len(preview.pages) > args.max_pages:
        print(f"\n  ... ({len(preview.pages) - args.max_pages} remaining pages omitted. Use --max-pages to see more)")

    if args.output:
        safe_save_json(args.output, preview.model_dump())


# -----------------------------------------------------------------------------
# Command 2: CHUNK (Inspection of Chunking Strategy & Overlap)
# -----------------------------------------------------------------------------
def handle_chunk(args: argparse.Namespace) -> None:
    doc_title = args.title

    if args.file:
        file_path: Path = args.file
        if not file_path.exists():
            print(f"[Error] File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        if not doc_title:
            doc_title = file_path.stem.replace("_", " ").title()

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        raw_pages = DocumentParser.parse(file_bytes, file_name=file_path.name)
        cleaned_pages = TextCleaner.clean_pages(raw_pages)
        input_pages = [{"page_number": p["page_number"], "text": p["cleaned_text"]} for p in cleaned_pages]
        input_text = None
    elif args.text:
        input_pages = None
        input_text = args.text
        if not doc_title:
            doc_title = "Direct Text Input"
    else:
        print("[Error] Please provide either --file <path> or --text '<content>' to chunk.", file=sys.stderr)
        sys.exit(1)

    print_banner(
        f"RAG PREVIEW: CHUNKING STRATEGY\n"
        f"  Document Title : {doc_title}\n"
        f"  Strategy       : {args.strategy}\n"
        f"  Target Size    : {args.chunk_size} chars | Overlap: {args.chunk_overlap} chars"
    )

    preview: ChunkPreviewResponse = TextChunker.generate_chunk_preview(
        text=input_text,
        pages=input_pages,
        strategy=args.strategy,
        document_title=doc_title,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    print_section("Chunking Analytics")
    print(f"  • Strategy Applied   : {preview.strategy}")
    print(f"  • Total Chunks       : {preview.total_chunks}")
    print(f"  • Average Tokens     : {preview.avg_tokens} tokens/chunk")

    total_tokens = sum(c.token_count for c in preview.chunks)
    print(f"  • Total Tokens Est.  : {total_tokens:,}")

    print_section(f"Generated Chunks (Showing {min(args.limit, len(preview.chunks))}/{len(preview.chunks)})")
    for chunk in preview.chunks[: args.limit]:
        heading = chunk.heading_path or "(Root Document Context)"
        print(f"\n  [Chunk #{chunk.chunk_index}] P.{chunk.page_number} | {chunk.token_count:3d} tokens")
        print(f"  Hierarchy: {heading}")
        if chunk.overlap_preview:
            print(f"  Overlap  : \"{chunk.overlap_preview[:80]}...\"")
        excerpt = chunk.content.replace("\n", " ").strip()[:180]
        print(f"  Content  : \"{excerpt}...\"")

    if len(preview.chunks) > args.limit:
        print(f"\n  ... ({len(preview.chunks) - args.limit} more chunks omitted. Use --limit to show more)")

    if args.output:
        safe_save_json(args.output, preview.model_dump())


# -----------------------------------------------------------------------------
# Command 3: RETRIEVE (Inspection of Vector Search & Prompt Assembly)
# -----------------------------------------------------------------------------
async def _async_handle_retrieve(args: argparse.Namespace) -> None:
    query: str = args.query.strip()
    category_id: UUID | None = None
    if args.category_id:
        try:
            category_id = UUID(args.category_id)
        except ValueError:
            print(f"[Error] Invalid category UUID: '{args.category_id}'", file=sys.stderr)
            sys.exit(1)

    print_banner(
        f"RAG PREVIEW: RETRIEVAL & PROMPT ASSEMBLY\n"
        f"  Query        : \"{query}\"\n"
        f"  Top K        : {args.top_k} | Score Threshold: {args.score_threshold}\n"
        f"  Category ID  : {category_id or '(All Categories)'}"
    )

    embedder = EmbeddingManager()
    vector_store = QdrantVectorStore()
    generation_manager = GenerationManager()
    rag_service = RAGService(
        embedder=embedder,
        vector_store=vector_store,
        generation_manager=generation_manager,
    )

    print("[1/2] Performing vector search against Qdrant Vector DB...")
    try:
        search_chunks = await rag_service.search(
            query=query,
            category_id=category_id,
            top_k=args.top_k,
            score_threshold=args.score_threshold,
        )
    except Exception as exc:
        print(f"\n[Warning] Search failed or Qdrant is unreachable: {exc}")
        print("  Make sure Docker Qdrant is running: 'docker compose up -d huce-kms-qdrant'")
        sys.exit(1)

    print(f"[2/2] Retrieved {len(search_chunks)} matching chunk(s). Assembling prompt preview...")
    preview: RetrievalPreviewResponse = RAGService.assemble_retrieval_preview(
        query=query,
        chunks=search_chunks,
    )

    print_section(f"Retrieved Chunks ({preview.total_found} Matches)")
    if not preview.retrieved_chunks:
        print("  (No chunks matched the score threshold or query criteria)")
    else:
        for item in preview.retrieved_chunks:
            print(f"\n  [Rank {item.rank}] Score: {item.score:.4f} | Document: \"{item.title}\"")
            print(f"    Page: {item.page_number} | Chunk Index: {item.chunk_index}")
            print(f"    Excerpt: \"{item.content_excerpt}\"")

    if args.show_prompt:
        print_section("Assembled System & User Prompt Preview")
        print(preview.assembled_prompt_preview)

    if args.output:
        safe_save_json(args.output, preview.model_dump())


def handle_retrieve(args: argparse.Namespace) -> None:
    asyncio.run(_async_handle_retrieve(args))


# -----------------------------------------------------------------------------
# Command 4: EVAL (Delegate to scripts/eval_pipeline.py)
# -----------------------------------------------------------------------------
def handle_eval(args: argparse.Namespace) -> None:
    eval_script = backend_root / "scripts" / "eval_pipeline.py"
    if not eval_script.exists():
        print(f"[Error] Eval pipeline script not found at: {eval_script}", file=sys.stderr)
        sys.exit(1)

    import subprocess

    cmd = [
        sys.executable,
        str(eval_script),
        "--file",
        str(args.file),
        "--query",
        args.query,
        "--strategy",
        args.strategy,
        "--top-k",
        str(args.top_k),
        "--threshold",
        str(args.threshold),
    ]
    if args.synthesis:
        cmd.append("--synthesis")
    if args.offline:
        cmd.append("--offline")
    if args.output_dir:
        cmd.extend(["--output-dir", str(args.output_dir)])

    print_banner(f"DELEGATING TO EVAL PIPELINE RUNNER\n  Command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


# -----------------------------------------------------------------------------
# CLI Parser Definition
# -----------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="huce-rag",
        description="HUCE-KMS RAG Developer CLI — Inspect, test, and tune RAG pipeline stages.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. extract
    p_extract = subparsers.add_parser("extract", help="Inspect text extraction and noise cleaning from document")
    p_extract.add_argument("--file", "-f", required=True, type=Path, help="Path to PDF, TXT, or DOCX document")
    p_extract.add_argument("--max-pages", "-p", type=int, default=3, help="Number of pages to inspect in stdout (default: 3)")
    p_extract.add_argument("--output", "-o", type=Path, default=None, help="Save structured JSON preview output")

    # 2. chunk
    p_chunk = subparsers.add_parser("chunk", help="Test chunking strategy, token counts, and heading breadcrumbs")
    p_chunk.add_argument("--file", "-f", type=Path, default=None, help="Document file to chunk")
    p_chunk.add_argument("--text", "-t", type=str, default=None, help="Direct raw text string to chunk")
    p_chunk.add_argument(
        "--strategy",
        "-s",
        type=str,
        default="legal_structural",
        choices=["legal_structural", "recursive"],
        help="Chunking strategy (default: 'legal_structural')",
    )
    p_chunk.add_argument("--chunk-size", "-c", type=int, default=settings.CHUNK_SIZE, help="Target chunk size in characters")
    p_chunk.add_argument("--chunk-overlap", "-l", type=int, default=settings.CHUNK_OVERLAP, help="Overlap in characters")
    p_chunk.add_argument("--title", type=str, default=None, help="Document title for contextual prefixing")
    p_chunk.add_argument("--limit", type=int, default=5, help="Number of chunks to display in stdout (default: 5)")
    p_chunk.add_argument("--output", "-o", type=Path, default=None, help="Save structured JSON preview output")

    # 3. retrieve
    p_retrieve = subparsers.add_parser("retrieve", help="Test semantic retrieval and prompt assembly against Qdrant")
    p_retrieve.add_argument("--query", "-q", required=True, type=str, help="Search query string")
    p_retrieve.add_argument("--top-k", "-k", type=int, default=3, help="Number of top chunks to retrieve (default: 3)")
    p_retrieve.add_argument("--score-threshold", type=float, default=0.35, help="Minimum cosine similarity score")
    p_retrieve.add_argument("--category-id", type=str, default=None, help="Filter by Category UUID")
    p_retrieve.add_argument("--show-prompt", action="store_true", help="Print the fully assembled system prompt")
    p_retrieve.add_argument("--output", "-o", type=Path, default=None, help="Save structured JSON preview output")

    # 4. eval
    p_eval = subparsers.add_parser("eval", help="Execute complete offline evaluation pipeline (extract -> chunk -> retrieve -> synthesis)")
    p_eval.add_argument("--file", "-f", required=True, type=Path, help="Target document file path")
    p_eval.add_argument("--query", "-q", required=True, type=str, help="Test query string")
    p_eval.add_argument("--strategy", "-s", type=str, default="legal_structural", choices=["legal_structural", "recursive"])
    p_eval.add_argument("--top-k", "-k", type=int, default=3, help="Top matches to score")
    p_eval.add_argument("--threshold", type=float, default=0.35, help="Similarity cutoff threshold")
    p_eval.add_argument("--synthesis", action="store_true", help="Include Step 4 (LLM Answer Generation via Gemini)")
    p_eval.add_argument("--offline", action="store_true", help="Use lexical token overlap instead of live Gemini embedding")
    p_eval.add_argument("--output-dir", "-o", type=Path, default=backend_root / "output" / "rag_eval", help="Directory for JSON artifacts")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "extract": handle_extract,
        "chunk": handle_chunk,
        "retrieve": handle_retrieve,
        "eval": handle_eval,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
