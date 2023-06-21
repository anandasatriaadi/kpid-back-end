import logging
import os
from typing import List

from app.api.exceptions import ApplicationException
from config import GOOGLE_BUCKET_NAME, GOOGLE_STORAGE_CLIENT

logger = logging.getLogger(__name__)

# main method to upload to gcs
def upload_to_gcloud(remote_dest: str, local_source: str):
    try:
        bucket = GOOGLE_STORAGE_CLIENT.bucket(GOOGLE_BUCKET_NAME)
        file_blob = bucket.blob(remote_dest)
        file_blob.upload_from_filename(local_source)
        file_blob.make_public()
    except Exception as err:
        logger.error(str(err))

# main method to downloads from gcs
def download_files_gcloud(local_dest: str, source: List[str]):
    try:
        bucket = GOOGLE_STORAGE_CLIENT.bucket(GOOGLE_BUCKET_NAME)
        for file in source:
            if os.path.exists(f"{local_dest}/{file.split('/')[-1]}"):
                continue
            file_blob = bucket.blob(file)
            filename = file.split("/")[-1]
            file_blob.download_to_filename(f"{local_dest}/{filename}")
    except Exception as err:
        logger.error(str(err))

def delete_file_gcloud(remote_blob_name):
    try:
        bucket = GOOGLE_STORAGE_CLIENT.bucket(GOOGLE_BUCKET_NAME)
        blob = bucket.blob(remote_blob_name)
        generation_match_precondition = None

        blob.reload()  # Fetch blob metadata to use in generation_match_precondition.
        generation_match_precondition = blob.generation

        blob.delete(if_generation_match=generation_match_precondition)

        print(f"Blob {remote_blob_name} deleted.")
    except Exception as err:
            logger.error(str(err))
