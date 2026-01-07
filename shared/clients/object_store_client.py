class ObjectStoreClient:
    """Stub for Object Store Client (e.g., S3/MinIO)."""
    def __init__(self, bucket: str):
        self.bucket = bucket
    
    def upload_file(self, file_path: str, key: str):
        print(f"[ObjectStore Stub] Uploading {file_path} to {key}")
    
    def download_file(self, key: str, dest_path: str):
        print(f"[ObjectStore Stub] Downloading {key} to {dest_path}")
