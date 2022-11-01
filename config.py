import os
from pymongo import MongoClient

# TODO REMOVE THIS URI FROM CODE
cluster = MongoClient(str(os.getenv('MONGO_URI')))
database = cluster["anndev"]

SECRET_KEY = str(os.getenv('SECRET_KEY'))
