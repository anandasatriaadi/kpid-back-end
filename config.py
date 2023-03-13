import os
from pymongo import MongoClient
from google.cloud import storage

# TODO REMOVE THIS URI FROM CODE
cluster = MongoClient(os.getenv('MONGO_URI'))
database = cluster["anndev"]


print("Connected to MongoDB " + os.getenv('MONGO_URI'))
SECRET_KEY = str(os.getenv('SECRET_KEY'))
STORAGE_CLIENT = storage.Client.from_service_account_json(
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
UPLOAD_PATH = f"{os.getcwd()}/uploads"
