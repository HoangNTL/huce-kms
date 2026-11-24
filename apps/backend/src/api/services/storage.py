import asyncio
import io
import logging
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from minio import Minio
from minio.error import S3Error

from api.core.config import settings

logger = logging.getLogger("huce_kms.services.storage")


class StorageService:
    """Enterprise Storage Service supporting both MinIO (S3-compatible) and local filesystem fallback."""

    @staticmethod
    def _clean_key(object_name: str) -> str:
        """Sanitize object path for consistent cross-platform keys."""
        return object_name.lstrip("/").replace("\\", "/")

    def __init__(
        self,
        backend: str | None = None,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        secure: bool | None = None,
        bucket_name: str | None = None,
        public_endpoint: str | None = None,
    ):
        self.backend = (backend or settings.STORAGE_BACKEND).lower()
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.secure = secure if secure is not None else settings.MINIO_SECURE
        self.bucket_name = bucket_name or settings.MINIO_BUCKET_NAME
        self.public_endpoint = public_endpoint or settings.MINIO_PUBLIC_ENDPOINT
        self.local_upload_dir = settings.UPLOAD_DIR

        self._minio_client: Minio | None = None
        self._bucket_verified = False

        if self.backend == "minio":
            try:
                self._minio_client = Minio(
                    endpoint=self.endpoint,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    secure=self.secure,
                )
            except Exception as e:
                logger.error("Failed to initialize MinIO client: %s. Falling back to local storage.", e)
                self.backend = "local"

    @property
    def client(self) -> Minio:
        if not self._minio_client:
            raise RuntimeError("MinIO client is not initialized.")
        return self._minio_client

    async def ensure_bucket_exists(self) -> bool:
        """Verify that the target MinIO bucket exists, creating it if needed."""
        if self.backend != "minio" or not self._minio_client:
            self.local_upload_dir.mkdir(parents=True, exist_ok=True)
            return True

        def _check_and_create() -> bool:
            try:
                if not self.client.bucket_exists(self.bucket_name):
                    logger.info("MinIO bucket '%s' does not exist. Creating it...", self.bucket_name)
                    self.client.make_bucket(self.bucket_name)
                    logger.info("MinIO bucket '%s' created successfully.", self.bucket_name)
                return True
            except Exception as e:
                logger.warning(
                    "MinIO service unreachable at '%s' (%s). Local storage fallback active.",
                    self.endpoint,
                    e,
                )
                return False

        exists = await asyncio.to_thread(_check_and_create)
        self._bucket_verified = exists
        return exists

    async def upload_file(
        self,
        file_bytes: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file bytes to MinIO object storage or local filesystem."""
        # Sanitize object key
        clean_object_name = self._clean_key(object_name)

        if self.backend == "minio" and self._minio_client:
            try:
                await self._ensure_bucket_once()

                def _put():
                    stream = io.BytesIO(file_bytes)
                    self.client.put_object(
                        bucket_name=self.bucket_name,
                        object_name=clean_object_name,
                        data=stream,
                        length=len(file_bytes),
                        content_type=content_type,
                    )

                await asyncio.to_thread(_put)
                logger.info("Successfully uploaded object '%s' to MinIO bucket '%s'", clean_object_name, self.bucket_name)
                return clean_object_name
            except Exception as e:
                logger.warning("MinIO upload failed for '%s': %s. Falling back to local storage.", clean_object_name, e)

        # Fallback to local filesystem
        target_path = self.local_upload_dir / clean_object_name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(target_path.write_bytes, file_bytes)
        logger.info("Saved file locally to: %s", target_path)
        return clean_object_name

    async def get_file(self, object_name: str) -> bytes:
        """Retrieve file bytes from MinIO or local filesystem."""
        clean_object_name = self._clean_key(object_name)

        # 1. Try MinIO if configured
        if self.backend == "minio" and self._minio_client:
            try:
                def _get() -> bytes:
                    response = self.client.get_object(self.bucket_name, clean_object_name)
                    try:
                        return response.read()
                    finally:
                        response.close()
                        response.release_conn()

                return await asyncio.to_thread(_get)
            except S3Error as s3e:
                logger.debug("Object '%s' not in MinIO: %s. Checking local fallback...", clean_object_name, s3e)
            except Exception as e:
                logger.warning("MinIO get_object error for '%s': %s. Checking local fallback...", clean_object_name, e)

        # 2. Try local filesystem (check relative to upload dir, or absolute if legacy)
        local_target = self.local_upload_dir / clean_object_name
        if local_target.exists():
            return await asyncio.to_thread(local_target.read_bytes)

        raw_path = Path(object_name)
        if raw_path.exists():
            return await asyncio.to_thread(raw_path.read_bytes)

        raise FileNotFoundError(f"File or object '{object_name}' not found in MinIO or local storage.")

    async def get_presigned_download_url(
        self,
        object_name: str,
        expiry_seconds: int | None = None,
        original_filename: str | None = None,
    ) -> str:
        """Generate a presigned GET URL for secure, direct file download from MinIO."""
        clean_object_name = self._clean_key(object_name)
        expires = timedelta(seconds=expiry_seconds or settings.MINIO_URL_EXPIRY_SECONDS)

        headers: dict[str, str] = {}
        if original_filename:
            headers["response-content-disposition"] = f'inline; filename="{original_filename}"'

        if self.backend == "minio" and self._minio_client:
            try:
                def _presign() -> str:
                    return self.client.get_presigned_url(
                        method="GET",
                        bucket_name=self.bucket_name,
                        object_name=clean_object_name,
                        expires=expires,
                        response_headers=headers or None,
                    )

                url = await asyncio.to_thread(_presign)

                # Rewrite public endpoint if configured (e.g. localhost:9000 for browser client)
                if self.public_endpoint:
                    parsed_public = urlparse(self.public_endpoint)
                    parsed_url = urlparse(url)
                    url = urlunparse(
                        (
                            parsed_public.scheme or parsed_url.scheme,
                            parsed_public.netloc or parsed_public.path,
                            parsed_url.path,
                            parsed_url.params,
                            parsed_url.query,
                            parsed_url.fragment,
                        )
                    )

                return url
            except Exception as e:
                logger.warning("Could not generate presigned URL for '%s': %s", clean_object_name, e)

        # Fallback local URL pointing to backend API endpoint
        return f"/api/v1/documents/raw/{clean_object_name}"

    async def delete_file(self, object_name: str) -> None:
        """Delete file from MinIO object storage and/or local filesystem."""
        clean_object_name = self._clean_key(object_name)

        # 1. MinIO removal
        if self.backend == "minio" and self._minio_client:
            try:
                def _delete():
                    self.client.remove_object(self.bucket_name, clean_object_name)

                await asyncio.to_thread(_delete)
                logger.info("Deleted object '%s' from MinIO bucket '%s'", clean_object_name, self.bucket_name)
            except Exception as e:
                logger.warning("MinIO delete failed for '%s': %s", clean_object_name, e)

        # 2. Local filesystem cleanup (for fallback or legacy files)
        local_target = self.local_upload_dir / clean_object_name
        if local_target.exists():
            try:
                await asyncio.to_thread(local_target.unlink)
            except Exception as e:
                logger.warning("Could not unlink local file '%s': %s", local_target, e)

        raw_path = Path(object_name)
        if raw_path.exists() and raw_path.is_file():
            try:
                await asyncio.to_thread(raw_path.unlink)
            except Exception as e:
                logger.warning("Could not unlink legacy file '%s': %s", raw_path, e)

    async def file_exists(self, object_name: str) -> bool:
        """Check if an object or file exists."""
        clean_object_name = self._clean_key(object_name)

        if self.backend == "minio" and self._minio_client:
            try:
                def _stat() -> bool:
                    try:
                        self.client.stat_object(self.bucket_name, clean_object_name)
                        return True
                    except S3Error:
                        return False

                if await asyncio.to_thread(_stat):
                    return True
            except Exception:
                pass

        local_target = self.local_upload_dir / clean_object_name
        if local_target.exists():
            return True

        return Path(object_name).exists()

    async def list_files_with_prefix(self, prefix: str) -> list[str]:
        """List object keys in storage matching a prefix."""
        clean_prefix = self._clean_key(prefix)

        # 1. MinIO listing
        if self.backend == "minio" and self._minio_client:
            try:
                def _list() -> list[str]:
                    objs = self.client.list_objects(self.bucket_name, prefix=clean_prefix, recursive=True)
                    return [o.object_name for o in objs if o.object_name]

                return await asyncio.to_thread(_list)
            except Exception as e:
                logger.warning("MinIO list_objects failed for prefix '%s': %s", clean_prefix, e)
                return []

        # 2. Local filesystem listing
        local_target = self.local_upload_dir / clean_prefix
        if local_target.exists():
            try:
                def _list_local() -> list[str]:
                    if local_target.is_dir():
                        return [
                            str(p.relative_to(self.local_upload_dir)).replace("\\", "/")
                            for p in local_target.rglob("*")
                            if p.is_file()
                        ]
                    return []

                return await asyncio.to_thread(_list_local)
            except Exception as e:
                logger.warning("Local list_objects failed for prefix '%s': %s", clean_prefix, e)

        return []

    async def _ensure_bucket_once(self) -> None:
        if not self._bucket_verified:
            await self.ensure_bucket_exists()


_storage_service_instance: StorageService | None = None


def get_storage_service() -> StorageService:
    """Return the global cached StorageService instance."""
    global _storage_service_instance
    if _storage_service_instance is None:
        _storage_service_instance = StorageService()
    return _storage_service_instance
