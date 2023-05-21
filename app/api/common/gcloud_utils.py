import logging
from typing import List

from app.api.exceptions import ApplicationException
from config import GOOGLE_BUCKET_NAME, GOOGLE_STORAGE_CLIENT

logger = logging.getLogger(__name__)

# ======== main method to upload to gcs ========
def upload_to_gcloud(destination: str, source: str):
    try:
        bucket = GOOGLE_STORAGE_CLIENT.bucket(GOOGLE_BUCKET_NAME)
        file_blob = bucket.blob(destination)
        file_blob.upload_from_filename(source)
        file_blob.make_public()
    except (TimeoutError, ApplicationException) as err:
        logger.error(err)

# ======== main method to downloads from gcs ========
def download_files_gcloud(destination: str, source: List[str]):
    try:
        bucket = GOOGLE_STORAGE_CLIENT.bucket(GOOGLE_BUCKET_NAME)
        for file in source:
            file_blob = bucket.blob(file)
            filename = file.split("/")[-1]
            file_blob.download_to_filename(f"{destination}/{filename}")
    except (TimeoutError, ApplicationException) as err:
        logger.error(err)