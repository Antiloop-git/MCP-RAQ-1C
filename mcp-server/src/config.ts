export const config = {
  qdrantHost: process.env.QDRANT_HOST ?? "qdrant",
  qdrantPort: parseInt(process.env.QDRANT_PORT ?? "6333", 10),
  embeddingServiceUrl: process.env.EMBEDDING_SERVICE_URL ?? "http://embeddings:5000",
  defaultCollection: process.env.DEFAULT_COLLECTION ?? "metadata_1c",
  port: parseInt(process.env.PORT ?? "8000", 10),
  host: process.env.HOST ?? "0.0.0.0",
  searchLimit: parseInt(process.env.SEARCH_LIMIT ?? "10", 10),
  // BSL Language Server (optional — syntax check tool available only when BSL_LS_URL is set)
  bslLsUrl: process.env.BSL_LS_URL ?? "http://bsl-ls:8005",
  // OData integration (optional — tools appear only when ODATA_URL is set)
  odataUrl: process.env.ODATA_URL ?? "",
  odataUser: process.env.ODATA_USER ?? "",
  odataPassword: process.env.ODATA_PASSWORD ?? "",
  odataTimeout: parseInt(process.env.ODATA_TIMEOUT ?? "30000", 10),
  // OData cache
  odataCacheEnabled: process.env.ODATA_CACHE_ENABLED !== "false",
  odataCacheTtlMs: parseInt(process.env.ODATA_CACHE_TTL ?? "300", 10) * 1000, // seconds → ms, default 5 min
  odataCacheMaxSize: parseInt(process.env.ODATA_CACHE_MAX_SIZE ?? "500", 10),
} as const;
