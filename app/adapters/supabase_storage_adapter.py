"""
Concrete implementation of StoragePort using Supabase Storage.
"""

from supabase import Client

from app.ports.storage_port import StoragePort


class SupabaseStorageAdapter(StoragePort):
    """Uploads and retrieves files via the Supabase Storage API."""

    def __init__(self, client: Client) -> None:
        self._client = client

    async def upload_file(
        self, bucket: str, path: str, file_bytes: bytes, content_type: str
    ) -> str:
        """Upload file to Supabase Storage and return the path."""
        self._client.storage.from_(bucket).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        return path

    async def get_signed_url(
        self, bucket: str, path: str, expires_in: int = 3600
    ) -> str:
        """Generate a signed download URL for a private file."""
        result = self._client.storage.from_(bucket).create_signed_url(
            path=path,
            expires_in=expires_in,
        )
        return result["signedURL"]
