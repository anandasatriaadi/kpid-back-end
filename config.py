import os

from google.cloud import storage
from pymongo import MongoClient

cluster = MongoClient(str(os.getenv('MONGO_URI')))
DATABASE = cluster["anndev"]

GOOGLE_STORAGE_CLIENT = storage.Client.from_service_account_json(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )
GOOGLE_BUCKET_NAME = str(os.getenv('GOOGLE_STORAGE_BUCKET_NAME'))
GOOGLE_EXTRACT_FRAME_URL = str(os.getenv('GOOGLE_FUNCTION_EXTRACT_FRAME'))
GOOGLE_MODERATE_FRAME_URL = str(os.getenv('GOOGLE_FUNCTION_MODERATE_FRAME'))
GOOGLE_MODERATE_AUDIO_URL = str(os.getenv('GOOGLE_FUNCTION_MODERATE_AUDIO'))

SECRET_KEY = str(os.getenv('SECRET_KEY'))
UPLOAD_PATH = f"{os.getcwd()}/uploads"
