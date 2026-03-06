import os


QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:5000")
PARSER_SERVICE_URL = os.getenv("PARSER_SERVICE_URL", "http://localhost:8001")
ROW_BATCH_SIZE = int(os.getenv("ROW_BATCH_SIZE", "200"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
VECTOR_DIMENSIONS = int(os.getenv("VECTOR_DIMENSIONS", "768"))
DEFAULT_COLLECTION = os.getenv("DEFAULT_COLLECTION", "metadata_1c")
