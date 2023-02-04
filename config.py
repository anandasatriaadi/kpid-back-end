import os
from pymongo import MongoClient

# TODO REMOVE THIS URI FROM CODE
cluster = MongoClient(os.getenv('MONGO_URI'))
database = cluster["anndev"]


print("Connected to MongoDB " + os.getenv('MONGO_URI'))
SECRET_KEY = str(os.getenv('SECRET_KEY'))
