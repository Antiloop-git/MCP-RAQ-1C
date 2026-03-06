import os


MODEL_NAME = os.getenv("MODEL_NAME", "sergeyzh/BERTA")
MODEL_DIMENSIONS = int(os.getenv("MODEL_DIMENSIONS", "768"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "32"))
SPARSE_MODEL_NAME = os.getenv("SPARSE_MODEL_NAME", "Qdrant/bm25")
