# HUCE-KMS Content Crawler — Phase 3 Implementation Plan: RAG Integration & Staging Ingestion

> **Project**: HUCE-KMS (Knowledge Management System & AI Assistant - Hanoi University of Civil Engineering)  
> **Module**: Content Crawler & RAG Ingestion Pipeline (Phase 3)  
> **Date**: 2026-11-11  
> **Approach**: Test-Driven Development (TDD) via Subagent-Driven Execution  

---

## 1. System Overview & Ingestion Architecture

Phase 3 connects the Crawl Artifacts generated in Phase 1 & 2 (`data/crawled/pages/<hash>/` and `data/crawled/sessions/<session_id>/`) with the existing RAG pipeline (`DocumentService`, PostgreSQL `Document`/`DocumentChunk`, and Qdrant Vector Store).

### Two-Stage Ingestion Strategy
1. **Staging / Draft Mode (`auto_publish=False`, Default)**:
   - Registers Document record in PostgreSQL with `status = "uploaded"`.
   - Saves file into `settings.UPLOAD_DIR`.
   - Does NOT invoke embedding model or push vector points to Qdrant.
   - Allows administrators to review, adjust categories, or discard unnecessary attachments before indexing.
2. **Direct Index Mode (`auto_publish=True`)**:
   - Executes full pipeline via `DocumentService.upload_and_process_document`: parsing, cleaning, structural chunking, Gemini embedding generation, and Qdrant vector upsert (`status = "indexed"`).

---

## 2. Directory Structure & Key Files

```text
apps/backend/src/api/services/crawler/
├── ingestion/
│   ├── __init__.py           # Package exports
│   ├── schemas.py            # IngestItemResult, IngestSummaryResponse DTOs
│   ├── reader.py             # CrawlArtifactReader (reads page and session directories)
│   └── adapter.py            # CrawlIngestionAdapter (orchestrates staging / indexing)
apps/backend/tools/crawler/
└── cli.py                    # Extended with `ingest` subcommand
apps/backend/tests/services/crawler/
├── test_ingest_reader.py     # Unit tests for artifact reader
├── test_ingestion_adapter.py # Unit tests for adapter (draft & auto-publish modes)
└── test_cli_ingest.py        # CLI parser and invocation tests
```

---

## 3. Implementation Tasks

### Task 1: Ingestion Schemas & Crawl Artifact Reader
- Create `apps/backend/src/api/services/crawler/ingestion/schemas.py`
- Create `apps/backend/src/api/services/crawler/ingestion/reader.py`
- Test: `apps/backend/tests/services/crawler/test_ingest_reader.py`

### Task 2: CrawlIngestionAdapter Service
- Create `apps/backend/src/api/services/crawler/ingestion/adapter.py`
- Export in `apps/backend/src/api/services/crawler/ingestion/__init__.py`
- Test: `apps/backend/tests/services/crawler/test_ingestion_adapter.py`

### Task 3: CLI Ingestion Subcommand
- Update `apps/backend/tools/crawler/cli.py` with `ingest` command
- Test: `apps/backend/tests/services/crawler/test_cli_ingest.py`

### Task 4: Real-World Ingestion Verification & Report
- Ingest real session `data/crawled/sessions/2026-11-10_121938/`
- Verify DB records and Qdrant points
- Generate `docs/analysis/crawler-phase3-verification-report.md`
