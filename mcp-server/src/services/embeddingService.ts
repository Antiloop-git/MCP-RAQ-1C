import { config } from "../config.js";
import type { EmbeddingResponse, SparseEmbeddingResponse } from "../types/metadata.js";

const baseUrl = config.embeddingServiceUrl;

// --- LRU Cache for embeddings ---
const CACHE_MAX = 256;

class LRUCache<V> {
  private cache = new Map<string, V>();
  constructor(private maxSize: number) {}

  get(key: string): V | undefined {
    const val = this.cache.get(key);
    if (val !== undefined) {
      // Move to end (most recently used)
      this.cache.delete(key);
      this.cache.set(key, val);
    }
    return val;
  }

  set(key: string, val: V): void {
    this.cache.delete(key);
    if (this.cache.size >= this.maxSize) {
      // Delete oldest (first key)
      const oldest = this.cache.keys().next().value;
      if (oldest !== undefined) this.cache.delete(oldest);
    }
    this.cache.set(key, val);
  }
}

const denseCache = new LRUCache<number[]>(CACHE_MAX);
const sparseCache = new LRUCache<{ indices: number[]; values: number[] }>(CACHE_MAX);

export async function embedText(text: string): Promise<number[]> {
  const cached = denseCache.get(text);
  if (cached) return cached;
  const response = await fetch(`${baseUrl}/embed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texts: [text], prefix: "search_query" }),
  });

  if (!response.ok) {
    throw new Error(
      `Embedding service error (dense): ${response.status} ${response.statusText}`
    );
  }

  const data = (await response.json()) as EmbeddingResponse;
  if (!data.embeddings?.[0]) {
    throw new Error("Embedding service returned empty dense embeddings");
  }
  denseCache.set(text, data.embeddings[0]);
  return data.embeddings[0];
}

export async function embedTextSparse(
  text: string
): Promise<{ indices: number[]; values: number[] }> {
  const cached = sparseCache.get(text);
  if (cached) return cached;
  const response = await fetch(`${baseUrl}/embed-sparse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texts: [text] }),
  });

  if (!response.ok) {
    throw new Error(
      `Embedding service error (sparse): ${response.status} ${response.statusText}`
    );
  }

  const data = (await response.json()) as SparseEmbeddingResponse;
  if (!data.embeddings?.[0]) {
    throw new Error("Embedding service returned empty sparse embeddings");
  }
  sparseCache.set(text, data.embeddings[0]);
  return data.embeddings[0];
}
