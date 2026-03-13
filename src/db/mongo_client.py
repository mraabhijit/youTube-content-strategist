from config import settings
from pymongo import MongoClient

client = MongoClient(settings.mongo_uri)
db = client[settings.mongo_db_name]
