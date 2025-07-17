import boto3
from botocore.client import Config
from fastapi import UploadFile
import uuid

from common.config import settings


class S3Client:
    def __init__(
        self,
        endpoint_url: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        bucket_name: str,
        secure: bool = False,
    ):
        self.endpoint_url = endpoint_url
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.bucket_name = bucket_name
        self.secure = secure
        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",  # or your region
        )

    def upload_file(self, file: UploadFile, object_name: str | None = None) -> str:
        """
        Upload a file to an S3 bucket.
        :param file: File to upload.
        :param object_name: S3 object name. If not specified, a unique name is generated.
        :return: The key of the uploaded object.
        """
        if object_name is None:
            # Generate a unique name for the file to avoid overwrites
            ext = file.filename.split(".")[-1]
            object_name = f"tests/{uuid.uuid4()}.{ext}"

        self.client.upload_fileobj(file.file, self.bucket_name, object_name)
        return object_name

    def get_public_url(self, object_key: str) -> str:
        """
        Get the public URL for a given object key.
        """
        # For local development, the host is localhost. In production, this should be the public domain.
        # We assume the port is the one exposed in docker-compose for MinIO.
        public_host = "localhost"
        protocol = "https" if self.secure else "http"
        return f"{protocol}://{public_host}:{settings.s3.port}/{self.bucket_name}/{object_key}"

    def delete_file(self, object_key: str):
        """
        Delete a file from an S3 bucket.
        :param object_key: The key of the object to delete.
        """
        self.client.delete_object(Bucket=self.bucket_name, Key=object_key)

    def get_key_from_url(self, url: str) -> str | None:
        """
        Extracts the object key from a public URL.
        :param url: The public URL of the S3 object.
        :return: The object key, or None if the URL is invalid.
        """
        try:
            # The key is the part of the path after the bucket name
            return url.split(f"{self.bucket_name}/")[1]
        except IndexError:
            return None


s3_client = S3Client(
    endpoint_url=f"http://{settings.s3.endpoint}",
    aws_access_key_id=settings.s3.access_key,
    aws_secret_access_key=settings.s3.secret_key,
    bucket_name=settings.s3.bucket,
)
