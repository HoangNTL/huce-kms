import shutil
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from api.services.storage import StorageService


class TestStorageService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_dir = Path("uploads_test")
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    async def test_local_storage_upload_and_get(self):
        service = StorageService(backend="local")
        service.local_upload_dir = self.test_dir

        test_data = b"Hello, HUCE-KMS Local Storage!"
        object_key = "documents/test_file.txt"

        # 1. Upload
        saved_key = await service.upload_file(
            file_bytes=test_data,
            object_name=object_key,
            content_type="text/plain",
        )
        self.assertEqual(saved_key, "documents/test_file.txt")

        # 2. Check existence
        exists = await service.file_exists(saved_key)
        self.assertTrue(exists)

        # 3. Read back
        read_bytes = await service.get_file(saved_key)
        self.assertEqual(read_bytes, test_data)

        # 4. Download URL (local fallback path)
        url = await service.get_presigned_download_url(saved_key, original_filename="test_file.txt")
        self.assertIn("/api/v1/documents/raw/", url)

        # 5. Delete
        await service.delete_file(saved_key)
        self.assertFalse(await service.file_exists(saved_key))

    @patch("api.services.storage.Minio")
    async def test_minio_storage_upload_and_presigned_url(self, mock_minio_cls):
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.get_presigned_url.return_value = (
            "http://localhost:9000/huce-kms-documents/documents/test.pdf?X-Amz-Signature=xyz"
        )
        mock_minio_cls.return_value = mock_client

        service = StorageService(
            backend="minio",
            endpoint="localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin123",
            secure=False,
            bucket_name="huce-kms-documents",
        )
        service._minio_client = mock_client
        service._bucket_verified = True

        test_pdf = b"%PDF-1.4 mock pdf content"
        object_name = "documents/sample.pdf"

        # Test upload
        saved_key = await service.upload_file(
            file_bytes=test_pdf,
            object_name=object_name,
            content_type="application/pdf",
        )
        self.assertEqual(saved_key, object_name)
        mock_client.put_object.assert_called_once()

        # Test presigned URL
        presigned_url = await service.get_presigned_download_url(
            object_name=object_name,
            expiry_seconds=3600,
            original_filename="sample.pdf",
        )
        self.assertTrue(presigned_url.startswith("http://localhost:9000"))
        mock_client.get_presigned_url.assert_called_once()

        # Test delete
        await service.delete_file(object_name)
        mock_client.remove_object.assert_called_once_with("huce-kms-documents", object_name)

    async def test_file_not_found_raises(self):
        service = StorageService(backend="local")
        service.local_upload_dir = self.test_dir
        with self.assertRaises(FileNotFoundError):
            await service.get_file("non_existent_path_xyz.pdf")


if __name__ == "__main__":
    unittest.main()
