import unittest
from datetime import datetime, timezone
from pydantic import ValidationError

from api.schemas.document import (
    DocumentDetailResponse,
    DocumentResponse,
)


class TestDocumentSchemas(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.base_data = {
            "id": 1,
            "title": "Tài liệu kiểm thử",
            "category_id": None,
            "file_name": "test.pdf",
            "file_path": "uploads/test.pdf",
            "file_size": 1024,
            "file_type": "pdf",
            "file_hash": "hash123456789",
            "uploader_id": 1,
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
        self.assertEqual(doc.status, "uploaded")

    def test_document_response_with_uppercase_status(self):
        data = {**self.base_data, "status": "UPLOADED"}
        doc = DocumentResponse.model_validate(data)
        self.assertEqual(doc.status, "uploaded")

        data_indexed = {**self.base_data, "status": "INDEXED"}
        doc_indexed = DocumentResponse.model_validate(data_indexed)
        self.assertEqual(doc_indexed.status, "indexed")

    def test_document_response_standard_statuses(self):
        for s in ["uploaded", "pending", "processing", "indexed", "failed"]:
            data = {**self.base_data, "status": s}
            doc = DocumentResponse.model_validate(data)
            self.assertEqual(doc.status, s)

    def test_document_detail_response_with_uploaded(self):
        data = {**self.base_data, "status": "uploaded", "chunks": []}
        doc = DocumentDetailResponse.model_validate(data)
        self.assertEqual(doc.status, "uploaded")
        self.assertEqual(doc.chunks, [])

    def test_invalid_status_raises_validation_error(self):
        data = {**self.base_data, "status": "completely_invalid_status"}
        with self.assertRaises(ValidationError):
            DocumentResponse.model_validate(data)


if __name__ == "__main__":
    unittest.main()
