import { LRUCache } from "lru-cache";
import { config } from "../config.js";

/**
 * OData client for 1C:Enterprise 8.3 standard OData interface.
 *
 * Base URL example: http://server/base/odata/standard.odata
 * Auth: HTTP Basic (1C user credentials)
 */

export interface ODataResponse<T = Record<string, unknown>> {
  value: T[];
}

export interface ODataError {
  "odata.error"?: {
    code: string;
    message: { lang: string; value: string };
  };
}

// --- LRU Cache ---

const cache = new LRUCache<string, unknown[]>({
  max: config.odataCacheMaxSize,
  ttl: config.odataCacheTtlMs,
});

function cacheKey(entitySet: string, params?: Record<string, string>): string {
  const sorted = params
    ? Object.keys(params).sort().map(k => `${k}=${params[k]}`).join("&")
    : "";
  return `${entitySet}?${sorted}`;
}

/** Cache statistics for health/debug endpoints */
export function odataCacheStats(): { enabled: boolean; size: number; ttlMs: number; maxSize: number } {
  return {
    enabled: config.odataCacheEnabled,
    size: cache.size,
    ttlMs: config.odataCacheTtlMs,
    maxSize: config.odataCacheMaxSize,
  };
}

/** Clear the OData cache (e.g. when data is known to have changed) */
export function odataCacheClear(): void {
  cache.clear();
}

// --- HTTP helpers ---

function getBaseUrl(): string {
  const url = config.odataUrl;
  if (!url) {
    throw new Error(
      "OData не настроен. Задайте переменную окружения ODATA_URL (например: http://server/base/odata/standard.odata)"
    );
  }
  return url.replace(/\/+$/, "");
}

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (config.odataUser) {
    const credentials = Buffer.from(
      `${config.odataUser}:${config.odataPassword ?? ""}`
    ).toString("base64");
    headers["Authorization"] = `Basic ${credentials}`;
  }
  return headers;
}

/**
 * Execute an OData GET request (with LRU cache).
 * @param entitySet - e.g. "AccumulationRegister_ДвижениеТМЦ_Balance"
 * @param params - OData query params ($filter, $select, $top, $orderby, etc.)
 */
export async function odataGet<T = Record<string, unknown>>(
  entitySet: string,
  params?: Record<string, string>
): Promise<T[]> {
  // Check cache
  if (config.odataCacheEnabled) {
    const key = cacheKey(entitySet, params);
    const cached = cache.get(key);
    if (cached) {
      return cached as T[];
    }
  }

  const base = getBaseUrl();
  // Encode each path segment separately to preserve '/' for FunctionImports
  // e.g. "AccumulationRegister_УчетПартий/Balance"
  const encodedPath = entitySet
    .split("/")
    .map((seg) => encodeURIComponent(seg))
    .join("/");
  const url = new URL(`${base}/${encodedPath}`);
  url.searchParams.set("$format", "json");
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      url.searchParams.set(key, value);
    }
  }

  const response = await fetch(url.toString(), {
    method: "GET",
    headers: getAuthHeaders(),
    signal: AbortSignal.timeout(config.odataTimeout),
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as ODataError;
      if (body["odata.error"]?.message?.value) {
        detail = body["odata.error"].message.value;
      }
    } catch {
      // ignore parse errors
    }
    throw new Error(`OData ошибка ${response.status}: ${detail}`);
  }

  const data = (await response.json()) as ODataResponse<T>;
  const result = data.value ?? [];

  // Store in cache
  if (config.odataCacheEnabled) {
    cache.set(cacheKey(entitySet, params), result);
  }

  return result;
}

/**
 * Check if OData is configured and reachable.
 */
export async function odataHealthCheck(): Promise<{
  ok: boolean;
  message: string;
}> {
  if (!config.odataUrl) {
    return { ok: false, message: "ODATA_URL не задан" };
  }
  try {
    const base = getBaseUrl();
    const response = await fetch(`${base}/?$format=json`, {
      method: "GET",
      headers: getAuthHeaders(),
      signal: AbortSignal.timeout(5000),
    });
    if (response.ok) {
      return { ok: true, message: "OData доступен" };
    }
    return { ok: false, message: `HTTP ${response.status}: ${response.statusText}` };
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    return { ok: false, message: msg };
  }
}

/**
 * Helper: build OData entity set name for 1C objects.
 *
 * 1C OData naming conventions:
 *   Catalog_Номенклатура
 *   Document_РеализацияТоваровУслуг
 *   AccumulationRegister_ДвижениеТМЦ_Balance (остатки)
 *   AccumulationRegister_ДвижениеТМЦ_Turnovers (обороты)
 *   AccumulationRegister_ДвижениеТМЦ (движения)
 *   InformationRegister_ЦеныНоменклатуры_SliceLast (срез последних)
 */
export function buildEntitySet(
  objectType: string,
  objectName: string,
  suffix?: "Balance" | "Turnovers" | "SliceLast" | "SliceFirst" | "RecordType"
): string {
  const parts = [objectType, objectName];
  if (suffix) parts.push(suffix);
  return parts.join("_");
}
