export const config = {
  qdrantHost: process.env.QDRANT_HOST ?? "qdrant",
  qdrantPort: parseInt(process.env.QDRANT_PORT ?? "6333", 10),
  embeddingServiceUrl: process.env.EMBEDDING_SERVICE_URL ?? "http://embeddings:5000",
  defaultCollection: process.env.DEFAULT_COLLECTION ?? "metadata_1c",
  port: parseInt(process.env.PORT ?? "8000", 10),
  host: process.env.HOST ?? "0.0.0.0",
  searchLimit: parseInt(process.env.SEARCH_LIMIT ?? "10", 10),
  // OData integration (optional — tools appear only when ODATA_URL is set)
  odataUrl: process.env.ODATA_URL ?? "",
  odataUser: process.env.ODATA_USER ?? "",
  odataPassword: process.env.ODATA_PASSWORD ?? "",
  odataTimeout: parseInt(process.env.ODATA_TIMEOUT ?? "30000", 10),
} as const;
