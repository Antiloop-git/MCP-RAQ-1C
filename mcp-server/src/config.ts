export const config = {
  qdrantHost: process.env.QDRANT_HOST ?? "qdrant",
  qdrantPort: parseInt(process.env.QDRANT_PORT ?? "6333", 10),
  embeddingServiceUrl: process.env.EMBEDDING_SERVICE_URL ?? "http://embeddings:5000",
  defaultCollection: process.env.DEFAULT_COLLECTION ?? "metadata_1c",
  port: parseInt(process.env.PORT ?? "8000", 10),
  host: process.env.HOST ?? "0.0.0.0",
  searchLimit: parseInt(process.env.SEARCH_LIMIT ?? "10", 10),
} as const;
