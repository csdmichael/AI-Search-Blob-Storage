"""
Upload documents from use-case data folder to Azure Blob Storage.

Uses managed identity (DefaultAzureCredential) for authentication.
Creates the container if it doesn't exist and uploads all documents.

Set USE_CASE env var to select: engineering_docs (default) or filter_design
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

STORAGE_ACCOUNT_NAME = config.storage_account_name()
CONTAINER_NAME = config.container_name()
STORAGE_URL = config.storage_url()
DATA_DIR = config.uc_data_dir()
_doc_cfg = config.uc_document_config()
FILE_FORMAT = _doc_cfg["file_format"]


def main():
    print(f"Connecting to storage account: {STORAGE_ACCOUNT_NAME}")
    credential = DefaultAzureCredential()
    blob_service_client = BlobServiceClient(account_url=STORAGE_URL, credential=credential)

    # Create container if it doesn't exist
    try:
        container_client = blob_service_client.create_container(CONTAINER_NAME)
        print(f"Created container: {CONTAINER_NAME}")
    except Exception as e:
        if "ContainerAlreadyExists" in str(e):
            print(f"Container '{CONTAINER_NAME}' already exists.")
            container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        else:
            raise

    # Upload all files from data directory
    if not os.path.exists(DATA_DIR):
        print(f"Error: Data directory not found: {DATA_DIR}")
        print("Run generate_docs.py first to create the engineering documents.")
        sys.exit(1)

    file_ext = f".{FILE_FORMAT}"
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(file_ext)]
    if not files:
        print(f"No {file_ext} files found in data directory.")
        sys.exit(1)

    print(f"\nUploading {len(files)} documents to container '{CONTAINER_NAME}'...")

    for i, filename in enumerate(sorted(files), 1):
        filepath = os.path.join(DATA_DIR, filename)
        blob_client = container_client.get_blob_client(filename)

        with open(filepath, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        print(f"  [{i}/{len(files)}] Uploaded: {filename}")

    print(f"\nSuccessfully uploaded {len(files)} documents to {STORAGE_URL}/{CONTAINER_NAME}")


if __name__ == "__main__":
    main()
