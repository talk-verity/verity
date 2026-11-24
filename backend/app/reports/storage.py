import logging
from pathlib import Path

from app.core.settings import settings

logger = logging.getLogger(__name__)

LOCAL_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "reports"


class ReportStorage:
    def upload(self, key: str, data: bytes, content_type: str = "text/html") -> str:
        raise NotImplementedError

    def download(self, key: str) -> bytes:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    @property
    def is_available(self) -> bool:
        return False


class S3ReportStorage(ReportStorage):
    def __init__(self):
        self.bucket = settings.R2_BUCKET_NAME
        self.endpoint_url = settings.r2_endpoint_url
        self.public_base_url = settings.R2_PUBLIC_BASE_URL
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name="auto",
            )
        return self._client

    def upload(self, key: str, data: bytes, content_type: str = "text/html") -> str:
        client = self._get_client()
        client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        if self.public_base_url:
            return f"{self.public_base_url.rstrip('/')}/{key}"
        return f"s3://{self.bucket}/{key}"

    def download(self, key: str) -> bytes:
        client = self._get_client()
        obj = client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()

    def delete(self, key: str) -> None:
        client = self._get_client()
        client.delete_object(Bucket=self.bucket, Key=key)

    @property
    def is_available(self) -> bool:
        return bool(settings.R2_ACCOUNT_ID and settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY)


class LocalReportStorage(ReportStorage):
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or LOCAL_STORAGE_DIR

    def _path(self, key: str) -> Path:
        base = self.base_dir.resolve()
        path = (base / key).resolve()
        if not path.is_relative_to(base) or path == base:
            raise ValueError("Invalid storage key")
        return path

    def upload(self, key: str, data: bytes, content_type: str = "text/html") -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path.as_uri()

    def download(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise FileNotFoundError(f"No stored report at {key}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    @property
    def is_available(self) -> bool:
        return True


def create_storage() -> ReportStorage:
    if settings.R2_ACCOUNT_ID and settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY:
        logger.info("Using Cloudflare R2 report storage")
        return S3ReportStorage()
    logger.warning("R2 not configured — using local report storage at %s", LOCAL_STORAGE_DIR)
    return LocalReportStorage()
