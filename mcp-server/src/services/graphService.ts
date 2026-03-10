import { QdrantClient } from "@qdrant/js-client-rest";
import { config } from "../config.js";

const client = new QdrantClient({
  host: config.qdrantHost,
  port: config.qdrantPort,
  checkCompatibility: false,
});

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DependencyRelation {
  name: string;
  type: string;
  direction: "forward" | "reverse";
}

export interface DependencyResult {
  query: string;
  direction: "forward" | "reverse" | "all";
  relations: DependencyRelation[];
}

// ---------------------------------------------------------------------------
// In-memory graph cache (per collection)
// ---------------------------------------------------------------------------

interface GraphCache {
  documentToRegisters: Map<string, string[]>;
  registerToDocuments: Map<string, string[]>;
}

const cacheByCollection = new Map<string, GraphCache>();

/**
 * Loads document→register dependencies from Qdrant using the scroll API.
 * Filters by object_type = "Document" and reads register_records payload.
 */
async function loadGraph(collectionName: string): Promise<GraphCache> {
  const documentToRegisters = new Map<string, string[]>();
  const registerToDocuments = new Map<string, string[]>();

  let offset: string | number | undefined = undefined;

  for (; ;) {
    const result = await client.scroll(collectionName, {
      filter: {
        must: [{ key: "object_type", match: { value: "Document" } }],
      },
      limit: 250,
      with_payload: ["object_name", "register_records"],
      ...(offset !== undefined ? { offset } : {}),
    });

    for (const point of result.points) {
      const p = point.payload as Record<string, unknown>;
      const docName = p.object_name as string;
      const records = p.register_records as string[] | undefined;

      if (!docName || !records || records.length === 0) continue;

      const registerFullNames: string[] = [];

      for (const raw of records) {
        // Format: "AccumulationRegister.ДвижениеТМЦ"
        const dotIndex = raw.indexOf(".");
        if (dotIndex === -1) continue;

        const regType = raw.substring(0, dotIndex);
        const regName = raw.substring(dotIndex + 1);

        registerFullNames.push(raw);

        // Reverse index: register short name → documents
        const existing = registerToDocuments.get(regName);
        if (existing) {
          if (!existing.includes(docName)) existing.push(docName);
        } else {
          registerToDocuments.set(regName, [docName]);
        }

        // Also index by full name (type.name) for reverse lookup
        const existingFull = registerToDocuments.get(raw);
        if (existingFull) {
          if (!existingFull.includes(docName)) existingFull.push(docName);
        } else {
          registerToDocuments.set(raw, [docName]);
        }
      }

      if (registerFullNames.length > 0) {
        documentToRegisters.set(docName, registerFullNames);
      }
    }

    if (!result.next_page_offset) break;
    offset = result.next_page_offset as string | number | undefined;
  }

  return { documentToRegisters, registerToDocuments };
}

/**
 * Returns the cached graph for the given collection, loading it on first call.
 */
async function getGraph(collectionName: string): Promise<GraphCache> {
  const cached = cacheByCollection.get(collectionName);
  if (cached) return cached;

  const graph = await loadGraph(collectionName);
  cacheByCollection.set(collectionName, graph);
  return graph;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Look up dependencies for a given object name.
 *
 * - `forward`  — treat `name` as a Document, return its registers
 * - `reverse`  — treat `name` as a Register, return documents that write to it
 * - `all`      — search in both directions
 */
export async function getDependencies(
  name: string,
  direction: "forward" | "reverse" | "all",
  collectionName: string = config.defaultCollection,
): Promise<DependencyResult> {
  const graph = await getGraph(collectionName);
  const relations: DependencyRelation[] = [];

  // Forward: Document → Registers
  if (direction === "forward" || direction === "all") {
    const registers = graph.documentToRegisters.get(name);
    if (registers) {
      for (const fullName of registers) {
        const dotIndex = fullName.indexOf(".");
        relations.push({
          name: fullName,
          type: dotIndex !== -1 ? fullName.substring(0, dotIndex) : "Register",
          direction: "forward",
        });
      }
    }
  }

  // Reverse: Register → Documents
  if (direction === "reverse" || direction === "all") {
    const documents = graph.registerToDocuments.get(name);
    if (documents) {
      for (const docName of documents) {
        relations.push({
          name: docName,
          type: "Document",
          direction: "reverse",
        });
      }
    }
  }

  return { query: name, direction, relations };
}

/**
 * Invalidate the cached graph for a collection (useful for testing or reload).
 */
export function invalidateGraphCache(collectionName?: string): void {
  if (collectionName) {
    cacheByCollection.delete(collectionName);
  } else {
    cacheByCollection.clear();
  }
}
