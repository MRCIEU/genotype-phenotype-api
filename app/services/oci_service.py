import oci
from typing import Optional
from datetime import datetime, timedelta
from app.config import get_settings
from app.logging_config import get_logger
from app.models.schemas import Singleton
import os
import io
import zipfile
import tempfile
import shutil

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

    def download_file(self, object_name: str, local_file_path: str) -> str:
        """
        Download a file from OCI Object Storage to local filesystem.

        Args:
            object_name: Name/path of the object in the bucket (with optional prefix)
            local_file_path: Path where the file should be saved locally

        Returns:
            Path to the downloaded file

        Raises:
            Exception: If download fails
        """
        try:
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

            response = self.object_storage_client.get_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                object_name=object_name,
            )

            with open(local_file_path, "wb") as f:
                for chunk in response.data.raw.stream(1024 * 1024, decode_content=False):
                    f.write(chunk)

            logger.info(f"Successfully downloaded {object_name} from bucket {self.bucket_name} to {local_file_path}")
            return local_file_path

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

    def download_and_zip_prefix(
        self, prefix: str, zip_filename: Optional[str] = None, temp_dir: Optional[str] = None
    ) -> io.BytesIO:
        """
        Download all files with a given prefix from OCI Object Storage and zip them.

        Args:
            prefix: The prefix/directory path in the bucket to download all files from
            zip_filename: Optional name for the zip file (defaults to prefix-based name)
            temp_dir: Optional temporary directory for downloads (defaults to system temp)

        Returns:
            BytesIO object containing the zip file

        Raises:
            Exception: If download or zip creation fails
        """
        temp_download_dir = None
        try:
            logger.info(f"Listing objects with prefix: {prefix}")
            list_objects_response = self.object_storage_client.list_objects(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                prefix=prefix,
            )

            objects = list_objects_response.data.objects
            if not objects:
                logger.warning(f"No objects found with prefix: {prefix}")
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                    pass
                zip_buffer.seek(0)
                return zip_buffer

            logger.info(f"Found {len(objects)} objects to download")

            if temp_dir:
                temp_download_dir = tempfile.mkdtemp(dir=temp_dir)
            else:
                temp_download_dir = tempfile.mkdtemp()

            downloaded_files = []
            for obj in objects:
                object_name = obj.name
                archive_name = object_name

                if archive_name == "" or archive_name.endswith("/"):
                    continue

                local_file_path = os.path.join(temp_download_dir, os.path.basename(archive_name))
                if "/" in archive_name:
                    local_subdir = os.path.join(temp_download_dir, os.path.dirname(archive_name))
                    os.makedirs(local_subdir, exist_ok=True)
                    local_file_path = os.path.join(local_subdir, os.path.basename(archive_name))

                try:
                    response = self.object_storage_client.get_object(
                        namespace_name=self.namespace,
                        bucket_name=self.bucket_name,
                        object_name=object_name,
                    )

                    # Write to local file
                    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                    with open(local_file_path, "wb") as f:
                        for chunk in response.data.raw.stream(1024 * 1024, decode_content=False):
                            f.write(chunk)

                    downloaded_files.append((local_file_path, archive_name))
                    logger.debug(f"Downloaded {object_name} to {local_file_path}")

                except Exception as e:
                    logger.error(f"Failed to download {object_name}: {e}")
                    # Continue with other files
                    continue

            if not downloaded_files:
                logger.warning("No files were successfully downloaded")
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                    pass
                zip_buffer.seek(0)
                return zip_buffer

            # Create zip file in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for local_path, archive_name in downloaded_files:
                    if os.path.exists(local_path):
                        zip_file.write(local_path, arcname=archive_name)
                        logger.debug(f"Added {archive_name} to zip")

            zip_buffer.seek(0)
            logger.info(f"Successfully created zip with {len(downloaded_files)} files from prefix {prefix}")

            return zip_buffer

        except Exception as e:
            logger.error(f"Failed to download and zip prefix {object_name}: {e}")
            raise
        finally:
            # Clean up temporary directory
            if temp_download_dir and os.path.exists(temp_download_dir):
                try:
                    shutil.rmtree(temp_download_dir)
                    logger.debug(f"Cleaned up temporary directory: {temp_download_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary directory {temp_download_dir}: {e}")
