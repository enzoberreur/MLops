"""
S3/Minio storage client for managing models and data.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List
import json
from datetime import datetime
import os

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config.config import S3_CONFIG


class S3Client:
    """S3/Minio client for object storage operations."""
    
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None,
        secure: bool = False
    ):
        """
        Initialize S3 client.
        
        Args:
            endpoint_url: S3 endpoint URL (for Minio)
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            region_name: AWS region
            secure: Use HTTPS
        """
        # Use provided values or defaults from config
        self.endpoint_url = endpoint_url or os.getenv('S3_ENDPOINT', S3_CONFIG['endpoint_url'])
        self.access_key = aws_access_key_id or os.getenv('S3_ACCESS_KEY', S3_CONFIG['aws_access_key_id'])
        self.secret_key = aws_secret_access_key or os.getenv('S3_SECRET_KEY', S3_CONFIG['aws_secret_access_key'])
        self.region = region_name or os.getenv('S3_REGION', S3_CONFIG['region_name'])
        
        # Configure client
        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(signature_version='s3v4')
        )
        
        logger.info(f"S3 client initialized: {self.endpoint_url}")
    
    def create_bucket(self, bucket_name: str) -> bool:
        """
        Create a bucket if it doesn't exist.
        
        Args:
            bucket_name: Name of the bucket
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket '{bucket_name}' already exists")
            return True
        except ClientError:
            try:
                self.client.create_bucket(Bucket=bucket_name)
                logger.info(f"Created bucket '{bucket_name}'")
                return True
            except ClientError as e:
                logger.error(f"Failed to create bucket '{bucket_name}': {e}")
                return False
    
    def upload_file(
        self,
        file_path: Path,
        bucket_name: str,
        object_name: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Upload a file to S3.
        
        Args:
            file_path: Local file path
            bucket_name: S3 bucket name
            object_name: S3 object name (defaults to filename)
            metadata: Optional metadata dictionary
        
        Returns:
            S3 URL if successful, None otherwise
        """
        if object_name is None:
            object_name = file_path.name
        
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = {k: str(v) for k, v in metadata.items()}
            
            self.client.upload_file(
                str(file_path),
                bucket_name,
                object_name,
                ExtraArgs=extra_args
            )
            
            url = f"{self.endpoint_url}/{bucket_name}/{object_name}"
            logger.info(f"Uploaded {file_path.name} to {url}")
            return url
        
        except ClientError as e:
            logger.error(f"Failed to upload {file_path}: {e}")
            return None
    
    def download_file(
        self,
        bucket_name: str,
        object_name: str,
        local_path: Path
    ) -> bool:
        """
        Download a file from S3.
        
        Args:
            bucket_name: S3 bucket name
            object_name: S3 object name
            local_path: Local destination path
        
        Returns:
            True if successful, False otherwise
        """
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(bucket_name, object_name, str(local_path))
            logger.info(f"Downloaded {object_name} to {local_path}")
            return True
        except ClientError as e:
            logger.error(f"Failed to download {object_name}: {e}")
            return False
    
    def list_objects(
        self,
        bucket_name: str,
        prefix: str = ""
    ) -> List[Dict]:
        """
        List objects in a bucket.
        
        Args:
            bucket_name: S3 bucket name
            prefix: Object prefix filter
        
        Returns:
            List of object dictionaries
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return []
            
            objects = []
            for obj in response['Contents']:
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                })
            
            return objects
        
        except ClientError as e:
            logger.error(f"Failed to list objects in {bucket_name}: {e}")
            return []
    
    def delete_object(self, bucket_name: str, object_name: str) -> bool:
        """
        Delete an object from S3.
        
        Args:
            bucket_name: S3 bucket name
            object_name: S3 object name
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_object(Bucket=bucket_name, Key=object_name)
            logger.info(f"Deleted {object_name} from {bucket_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete {object_name}: {e}")
            return False
    
    def get_object_metadata(
        self,
        bucket_name: str,
        object_name: str
    ) -> Optional[Dict]:
        """
        Get object metadata.
        
        Args:
            bucket_name: S3 bucket name
            object_name: S3 object name
        
        Returns:
            Metadata dictionary or None
        """
        try:
            response = self.client.head_object(
                Bucket=bucket_name,
                Key=object_name
            )
            return response.get('Metadata', {})
        except ClientError as e:
            logger.error(f"Failed to get metadata for {object_name}: {e}")
            return None
    
    def bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if a bucket exists.
        
        Args:
            bucket_name: S3 bucket name
        
        Returns:
            True if exists, False otherwise
        """
        try:
            self.client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError:
            return False
    
    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """
        Check if an object exists.
        
        Args:
            bucket_name: S3 bucket name
            object_name: S3 object name
        
        Returns:
            True if exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=bucket_name, Key=object_name)
            return True
        except ClientError:
            return False
    
    def get_presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate a presigned URL for temporary access.
        
        Args:
            bucket_name: S3 bucket name
            object_name: S3 object name
            expiration: URL expiration time in seconds
        
        Returns:
            Presigned URL or None
        """
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': object_name},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None


def get_s3_client() -> S3Client:
    """Get a configured S3 client instance."""
    return S3Client()


if __name__ == "__main__":
    # Test S3 client
    logger.info("Testing S3 client...")
    
    client = get_s3_client()
    
    # Create test bucket
    bucket_name = "test-bucket"
    client.create_bucket(bucket_name)
    
    # List buckets
    logger.info("Testing complete!")
