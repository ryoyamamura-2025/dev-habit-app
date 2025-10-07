import os
from google.cloud import firestore

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_FIRESTORE_DB_NAME=os.getenv("GCP_FIRESTORE_DB_NAME")

# クライアントの初期化
db = firestore.AsyncClient(database=GCP_FIRESTORE_DB_NAME)