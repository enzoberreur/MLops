"""
Model storage and versioning utilities for S3/Minio.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List
import json
from datetime import datetime
import hashlib
import shutil

from loguru import logger

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.storage.s3_client import S3Client
from src.config.config import S3_BUCKET_NAME


class ModelStorage:
    """Manage model storage in S3/Minio with versioning."""
    
    def __init__(
        self,
        s3_client: Optional[S3Client] = None,
        bucket_name: str = "models"
    ):
        """
        Initialize model storage.
        
        Args:
            s3_client: S3Client instance
            bucket_name: Bucket name for models
        """
        self.s3_client = s3_client or S3Client()
        self.bucket_name = bucket_name
        
        # Ensure bucket exists
        self.s3_client.create_bucket(bucket_name)
    
    def upload_model(
        self,
        model_path: Path,
        model_name: str,
        version: Optional[str] = None,
        metadata: Optional[Dict] = None,
        additional_files: Optional[List[Path]] = None
    ) -> Dict:
        """
        Upload a model to S3 with versioning.
        
        Args:
            model_path: Path to model checkpoint
            model_name: Model name
            version: Version string (auto-generated if None)
            metadata: Model metadata
            additional_files: Additional files to upload (e.g., config, history)
        
        Returns:
            Dictionary with upload information
        """
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Generate version if not provided
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create model directory in S3
        model_dir = f"{model_name}/v{version}"
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'model_name': model_name,
            'version': version,
            'upload_time': datetime.now().isoformat(),
            'file_size': str(model_path.stat().st_size)
        })
        
        # Calculate checksum
        checksum = self._calculate_checksum(model_path)
        metadata['checksum'] = checksum
        
        # Upload main model file
        model_object_name = f"{model_dir}/{model_path.name}"
        model_url = self.s3_client.upload_file(
            file_path=model_path,
            bucket_name=self.bucket_name,
            object_name=model_object_name,
            metadata=metadata
        )
        
        if model_url is None:
            raise Exception("Failed to upload model")
        
        # Upload additional files
        uploaded_files = [model_url]
        
        if additional_files:
            for file_path in additional_files:
                if file_path.exists():
                    object_name = f"{model_dir}/{file_path.name}"
                    url = self.s3_client.upload_file(
                        file_path=file_path,
                        bucket_name=self.bucket_name,
                        object_name=object_name,
                        metadata={'model_version': version}
                    )
                    if url:
                        uploaded_files.append(url)
        
        # Create and upload manifest
        manifest = {
            'model_name': model_name,
            'version': version,
            'model_file': model_object_name,
            'model_url': model_url,
            'checksum': checksum,
            'metadata': metadata,
            'additional_files': uploaded_files[1:],
            'created_at': datetime.now().isoformat()
        }
        
        manifest_path = Path(f"/tmp/{model_name}_v{version}_manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        manifest_object_name = f"{model_dir}/manifest.json"
        manifest_url = self.s3_client.upload_file(
            file_path=manifest_path,
            bucket_name=self.bucket_name,
            object_name=manifest_object_name
        )
        
        manifest_path.unlink()  # Clean up temp file
        
        logger.success(f"Model uploaded successfully: {model_name} v{version}")
        logger.info(f"Model URL: {model_url}")
        logger.info(f"Manifest URL: {manifest_url}")
        
        return manifest
    
    def download_model(
        self,
        model_name: str,
        version: str,
        local_dir: Path,
        download_additional: bool = True
    ) -> Path:
        """
        Download a model from S3.
        
        Args:
            model_name: Model name
            version: Version string (with or without 'v' prefix)
            local_dir: Local directory to download to
            download_additional: Download additional files
        
        Returns:
            Path to downloaded model file
        """
        # Ensure version has 'v' prefix
        if not version.startswith('v'):
            version = f"v{version}"
        model_dir = f"{model_name}/{version}"
        local_dir = Path(local_dir)
        local_dir.mkdir(parents=True, exist_ok=True)
        
        # Download manifest first
        manifest_object = f"{model_dir}/manifest.json"
        manifest_path = local_dir / "manifest.json"
        
        if not self.s3_client.download_file(
            bucket_name=self.bucket_name,
            object_name=manifest_object,
            local_path=manifest_path
        ):
            raise Exception(f"Failed to download manifest for {model_name} v{version}")
        
        # Load manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Download main model file
        model_object = manifest['model_file']
        model_filename = Path(model_object).name
        model_path = local_dir / model_filename
        
        if not self.s3_client.download_file(
            bucket_name=self.bucket_name,
            object_name=model_object,
            local_path=model_path
        ):
            raise Exception(f"Failed to download model file")
        
        # Verify checksum
        checksum = self._calculate_checksum(model_path)
        if checksum != manifest['checksum']:
            logger.warning(f"Checksum mismatch for {model_filename}")
        
        # Download additional files if requested
        if download_additional and 'additional_files' in manifest:
            for file_url in manifest['additional_files']:
                file_name = Path(file_url).name
                file_object = f"{model_dir}/{file_name}"
                file_path = local_dir / file_name
                self.s3_client.download_file(
                    bucket_name=self.bucket_name,
                    object_name=file_object,
                    local_path=file_path
                )
        
        logger.success(f"Model downloaded: {model_path}")
        return model_path
    
    def list_model_versions(self, model_name: str) -> List[Dict]:
        """
        List all versions of a model.
        
        Args:
            model_name: Model name
        
        Returns:
            List of version dictionaries
        """
        prefix = f"{model_name}/"
        objects = self.s3_client.list_objects(
            bucket_name=self.bucket_name,
            prefix=prefix
        )
        
        # Extract unique versions
        versions = set()
        for obj in objects:
            parts = obj['key'].split('/')
            if len(parts) >= 2 and parts[1].startswith('v'):
                versions.add(parts[1])
        
        # Get manifest for each version
        version_info = []
        for version in sorted(versions, reverse=True):
            manifest_key = f"{model_name}/{version}/manifest.json"
            if self.s3_client.object_exists(self.bucket_name, manifest_key):
                metadata = self.s3_client.get_object_metadata(
                    self.bucket_name,
                    manifest_key
                )
                version_info.append({
                    'version': version,
                    'manifest_key': manifest_key
                })
        
        return version_info
    
    def get_latest_version(self, model_name: str) -> Optional[str]:
        """
        Get the latest version of a model.
        
        Args:
            model_name: Model name
        
        Returns:
            Latest version string or None
        """
        versions = self.list_model_versions(model_name)
        if versions:
            return versions[0]['version']
        return None
    
    def delete_model_version(
        self,
        model_name: str,
        version: str
    ) -> bool:
        """
        Delete a specific model version.
        
        Args:
            model_name: Model name
            version: Version to delete
        
        Returns:
            True if successful
        """
        model_dir = f"{model_name}/{version}"
        objects = self.s3_client.list_objects(
            bucket_name=self.bucket_name,
            prefix=model_dir
        )
        
        success = True
        for obj in objects:
            if not self.s3_client.delete_object(self.bucket_name, obj['key']):
                success = False
        
        if success:
            logger.info(f"Deleted {model_name} {version}")
        
        return success
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of a file."""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()


if __name__ == "__main__":
    # Test model storage
    logger.info("Testing model storage...")
    
    storage = ModelStorage()
    
    # List models
    logger.info("Model storage initialized successfully")
