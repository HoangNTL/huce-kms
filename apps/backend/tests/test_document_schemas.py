import unittest
from datetime import datetime, timezone
from uuid import UUID
from pydantic import ValidationError

from api.constants.enums import DocumentStatus
from api.schemas.document import (
    DocumentDetailResponse,
    DocumentResponse,
)


class TestDocumentSchemas(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.doc_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef0")
        self.user_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef1")
        self.base_data = {
            "id": self.doc_id,
            "title": "Tài liệu kiểm thử",
            "category_id": None,
            "file_name": "test.pdf",
            "file_path": "uploads/test.pdf",
            "file_size": 1024,
            "file_type": "pdf",
            "file_hash": "hash123456789",
            "created_by_id": self.user_id,
            "total_pages": 1,
            "chunk_count": 0,
            "error_message": None,
            "created_at": self.now,
            "updated_at": self.now,
            "category": None,
        }

    def test_document_response_with_uploaded_status(self):
        data = {**self.base_data, "status": "uploaded"}
        doc = DocumentResponse.model_validate(data)
        self.assertEqual(doc.status, DocumentStatus.UPLOADED)
        self.assertEqual(doc.status_name, "uploaded")

    def test_document_response_with_uppercase_status(self):
        data = {**self.base_data, "status": "UPLOADED"}
        doc = DocumentResponse.model_validate(data)
        self.assertEqual(doc.status, DocumentStatus.UPLOADED)
        self.assertEqual(doc.status_name, "uploaded")

        data_indexed = {**self.base_data, "status": "INDEXED"}
        doc_indexed = DocumentResponse.model_validate(data_indexed)
        self.assertEqual(doc_indexed.status, DocumentStatus.INDEXED)
        self.assertEqual(doc_indexed.status_name, "indexed")

    def test_document_response_standard_statuses(self):
        for s in ["uploaded", "pending", "processing", "indexed", "failed"]:
            data = {**self.base_data, "status": s}
            doc = DocumentResponse.model_validate(data)
            self.assertEqual(doc.status_name, s)
            self.assertEqual(doc.status, DocumentStatus.from_str(s))

    def test_document_detail_response_with_uploaded(self):
        data = {**self.base_data, "status": "uploaded", "chunks": []}
        doc = DocumentDetailResponse.model_validate(data)
        self.assertEqual(doc.status, DocumentStatus.UPLOADED)
        self.assertEqual(doc.status_name, "uploaded")
        self.assertEqual(doc.chunks, [])

    def test_invalid_status_raises_validation_error(self):
        data = {**self.base_data, "status": "completely_invalid_status"}
        with self.assertRaises(ValidationError):
            DocumentResponse.model_validate(data)


if __name__ == "__main__":
    unittest.main()
