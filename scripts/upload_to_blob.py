"""
Upload engineering documents from data folder to Azure Blob Storage.

Uses managed identity (DefaultAzureCredential) for authentication.
Creates the 'engineering-docs' container if it doesn't exist and uploads all documents.
"""

import os
import sys
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import config

config.validate_required(["STORAGE_ACCOUNT_NAME", "STORAGE_CONTAINER_NAME"])

STORAGE_ACCOUNT_NAME = config.STORAGE_ACCOUNT_NAME
CONTAINER_NAME = config.STORAGE_CONTAINER_NAME
STORAGE_URL = config.STORAGE_URL

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


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

    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".txt")]
    if not files:
        print("No .txt files found in data directory.")
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
