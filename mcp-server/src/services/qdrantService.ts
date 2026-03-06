import { QdrantClient } from "@qdrant/js-client-rest";
import { config } from "../config.js";
import { embedText, embedTextSparse } from "./embeddingService.js";
import type {
  SearchResult,
  MetadataDetails,
  ObjectTypeStats,
} from "../types/metadata.js";

const client = new QdrantClient({
  host: config.qdrantHost,
  port: config.qdrantPort,
  checkCompatibility: false,
});

export interface HybridSearchOptions {
  objectType?: string;
  limit?: number;
  collectionName?: string;
}

export async function hybridSearch(
  query: string,
  options: HybridSearchOptions = {}
): Promise<SearchResult[]> {
  const {
    objectType,
    limit = config.searchLimit,
    collectionName = config.defaultCollection,
  } = options;

  const [dense, sparse] = await Promise.all([
    embedText(query),
    embedTextSparse(query),
  ]);

  const filter = objectType
    ? {
        must: [
          {
            key: "object_type",
            match: { any: [objectType] },
          },
        ],
      }
    : undefined;

  const results = await client.query(collectionName, {
    prefetch: [
      { query: dense, using: "object_name", limit: 20 },
      { query: dense, using: "friendly_name", limit: 20 },
      {
        query: {
          indices: sparse.indices,
          values: sparse.values,
        },
        using: "bm25",
        limit: 20,
      },
    ],
    query: { fusion: "rrf" },
    filter,
    limit,
    with_payload: true,
  });

  return (results.points || []).map((point: any) => {
    const p = point.payload as Record<string, unknown>;
    return {
      name: p.object_name as string,
      synonym: p.synonym as string,
      objectType: p.object_type as string,
      objectTypeRu: p.object_type_ru as string,
      score: (point.score as number) ?? 0,
    };
  });
}

export async function getObjectByName(
  name: string,
  collectionName: string = config.defaultCollection,
  objectType?: string
): Promise<MetadataDetails | null> {
  const must: Array<Record<string, unknown>> = [
    { key: "object_name", match: { value: name } },
  ];
  if (objectType) {
    must.push({ key: "object_type", match: { value: objectType } });
  }

  const result = await client.scroll(collectionName, {
    filter: { must },
    limit: 1,
    with_payload: true,
  });

  const point = result.points[0];
  if (!point) return null;

  return point.payload as unknown as MetadataDetails;
}

export async function getObjectTypeStats(
  collectionName: string = config.defaultCollection
): Promise<ObjectTypeStats[]> {
  const statsMap = new Map<string, { typeRu: string; count: number }>();
  let offset: string | number | undefined = undefined;

  for (;;) {
    const result = await client.scroll(collectionName, {
      limit: 250,
      with_payload: ["object_type", "object_type_ru"],
      ...(offset !== undefined ? { offset } : {}),
    });

    for (const point of result.points) {
      const p = point.payload as Record<string, unknown>;
      const type = p.object_type as string;
      const typeRu = p.object_type_ru as string;
      const existing = statsMap.get(type);
      if (existing) {
        existing.count++;
      } else {
        statsMap.set(type, { typeRu, count: 1 });
      }
    }

    if (!result.next_page_offset) break;
    offset = result.next_page_offset as string | number | undefined;
  }

  return Array.from(statsMap.entries())
    .map(([type, { typeRu, count }]) => ({ type, typeRu, count }))
    .sort((a, b) => b.count - a.count);
}
