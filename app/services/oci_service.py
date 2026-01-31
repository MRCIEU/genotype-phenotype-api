import oci
from typing import Optional
from datetime import datetime, timedelta
from app.config import get_settings
from app.logging_config import get_logger
from app.models.schemas import Singleton
import os

settings = get_settings()
logger = get_logger(__name__)


class OCIService(metaclass=Singleton):
    """
    Service for interacting with Oracle Cloud Infrastructure (OCI) Object Storage.
    Handles file uploads, downloads, deletions, and other bucket operations.
    """

    def __init__(self):
        """
        Initialize OCI Object Storage client.

        Uses an Oracle policy which allows all instances in a dynamic group to access resources in a given
        compartment. In this case, all gpmap instances can read from the gpmap bucket.
        """
        self.bucket_name = settings.OCI_BUCKET_NAME
        self.namespace = settings.OCI_NAMESPACE

        if not self.namespace:
            raise ValueError("OCI Object Storage not configured. OCIService is disabled.")

        try:
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            self.object_storage_client = oci.object_storage.ObjectStorageClient(config={}, signer=signer)
            self.region = signer.region
        except Exception as e:
            logger.error(f"Failed to initialize OCI client: {e}")
            raise

    def upload_file(
        self,
        local_file_path: str,
        object_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Upload a file to OCI Object Storage.

        Args:
            local_file_path: Path to the local file to upload
            object_name: Name/path of the object in the bucket (with optional prefix)
            content_type: MIME type of the file (optional, will be inferred if not provided)
            metadata: Optional metadata dictionary to attach to the object

        Returns:
            The full object name (with prefix) that was uploaded

        Raises:
            Exception: If upload fails
        """
        try:
            with open(local_file_path, "rb") as file_content:
                file_data = file_content.read()

            if not content_type:
                import mimetypes

                content_type, _ = mimetypes.guess_type(local_file_path)
                if not content_type:
                    content_type = "application/octet-stream"

            put_kwargs = {
                "namespace_name": self.namespace,
                "bucket_name": self.bucket_name,
                "object_name": object_name,
                "put_object_body": file_data,
                "content_type": content_type,
            }
            if metadata:
                put_kwargs["opc_meta"] = metadata

            self.object_storage_client.put_object(**put_kwargs)

            logger.info(f"Successfully uploaded {local_file_path} to {object_name} in bucket {self.bucket_name}")
            return object_name

        except Exception as e:
            logger.error(f"Failed to upload file {local_file_path} to OCI: {e}")
            raise

    def get_file(self, object_name: str, download_to_local_file: bool = False, local_file_path: str = None) -> str:
        """
        Download a file from OCI Object Storage to local filesystem.

        Args:
            object_name: Name/path of the object in the bucket (with optional prefix)
            download_to_local_file: Whether to download the file to the local filesystem
            local_file_path: Path where the file should be saved locally if download_to_local_file is True

        Returns:
            Path to the downloaded file if download_to_local_file is True, otherwise the file content

        Raises:
            Exception: If download fails
        """
        try:
            response = self.object_storage_client.get_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
            if download_to_local_file:
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                with open(local_file_path, "wb") as f:
                    for chunk in response.data.raw.stream(1024 * 1024, decode_content=False):
                        f.write(chunk)
                logger.info(
                    f"Successfully downloaded {object_name} from bucket {self.bucket_name} to {local_file_path}"
                )
                return local_file_path
            else:
                return response.data.content
        except Exception as e:
            logger.error(f"Failed to download file {object_name} from OCI: {e}")
            raise

    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from OCI Object Storage.

        Args:
            object_name: Name/path of the object in the bucket (with optional prefix)

        Returns:
            True if deletion was successful

        Raises:
            Exception: If deletion fails
        """
        try:
            self.object_storage_client.delete_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                object_name=object_name,
            )

            logger.info(f"Successfully deleted {object_name} from bucket {self.bucket_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete file {object_name} from OCI: {e}")
            raise

    def get_file_url(self, object_name: str, expires_in_seconds: int = 3600) -> str:
        """
        Generate a pre-signed URL for accessing a file in OCI Object Storage.

        Args:
            object_name: Name/path of the object in the bucket (with optional prefix)
            expires_in_seconds: URL expiration time in seconds (default: 1 hour)

        Returns:
            Pre-signed URL string

        Raises:
            Exception: If URL generation fails
        """
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
            create_preauth_request_details = oci.object_storage.models.CreatePreauthenticatedRequestDetails(
                name=f"temp-access-{object_name}",
                object_name=object_name,
                access_type=oci.object_storage.models.CreatePreauthenticatedRequestDetails.ACCESS_TYPE_OBJECT_READ,
                time_expires=expires_at,
            )

            response = self.object_storage_client.create_preauthenticated_request(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                create_preauthenticated_request_details=create_preauth_request_details,
            )

            base_url = f"https://objectstorage.{self.region}.oraclecloud.com"
            url = f"{base_url}{response.data.access_uri}"

            logger.info(f"Generated pre-signed URL for {object_name}")
            return url

        except Exception as e:
            logger.error(f"Failed to generate pre-signed URL for {object_name}: {e}")
            raise

    def delete_prefix(self, prefix: str) -> bool:
        """
        Delete all objects with a given prefix from OCI Object Storage.

        Args:
            prefix: The prefix/directory path in the bucket to delete all files from

        Returns:
            True if all deletions were successful

        Raises:
            Exception: If deletion fails
        """
        try:
            logger.info(f"Listing objects with prefix for deletion: {prefix}")
            list_objects_response = self.object_storage_client.list_objects(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                prefix=prefix,
            )

            objects = list_objects_response.data.objects
            if not objects:
                logger.warning(f"No objects found with prefix to delete: {prefix}")
                return True

            logger.info(f"Found {len(objects)} objects to delete")

            for obj in objects:
                self.delete_file(obj.name)

            return True

        except Exception as e:
            logger.error(f"Failed to delete objects with prefix {prefix}: {e}")
            raise
