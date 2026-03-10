/**
 * SubsystemService — загрузка дерева подсистем из parsed_metadata/all_metadata.json.
 *
 * Qdrant-коллекция НЕ содержит полей content / child_subsystems для подсистем,
 * поэтому данные берутся напрямую из JSON-файла (он доступен как маунт в Docker
 * или локально при разработке).
 */

import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Запись подсистемы в JSON-файле метаданных */
interface RawMetadataEntry {
  name: string;
  synonym?: string;
  object_type: string;
  content?: string[];
  child_subsystems?: string[];
  [key: string]: unknown;
}

export interface SubsystemInfo {
  name: string;
  synonym: string;
  content: string[];
  children: string[];
}

export interface SubsystemTreeEntry {
  name: string;
  synonym: string;
  objectCount: number;
  childCount: number;
}

export interface SubsystemContentResult {
  name: string;
  synonym: string;
  objects: string[];
  /** Включённые дочерние подсистемы (только при recursive=true) */
  includedSubsystems?: string[];
}

export interface ObjectSubsystemsResult {
  objectName: string;
  subsystems: Array<{ name: string; synonym: string }>;
}

// ---------------------------------------------------------------------------
// Cache
// ---------------------------------------------------------------------------

interface SubsystemCache {
  subsystemMap: Map<string, SubsystemInfo>;
  objectToSubsystems: Map<string, string[]>;
  topLevelSubsystems: string[];
}

let cache: SubsystemCache | null = null;
let loadingPromise: Promise<SubsystemCache> | null = null;

// ---------------------------------------------------------------------------
// JSON file resolution
// ---------------------------------------------------------------------------

const CANDIDATE_PATHS = [
  "/app/parsed_metadata/all_metadata.json",        // Docker mount
  resolve(__dirname, "../../../parsed_metadata/all_metadata.json"), // local dev (relative to dist/)
  resolve(process.cwd(), "parsed_metadata/all_metadata.json"),      // CWD
];

function resolveJsonPath(): string {
  const envPath = process.env.METADATA_JSON_PATH;
  if (envPath) {
    if (existsSync(envPath)) return envPath;
    throw new Error(`METADATA_JSON_PATH="${envPath}" не найден`);
  }

  for (const candidate of CANDIDATE_PATHS) {
    if (existsSync(candidate)) return candidate;
  }

  throw new Error(
    "all_metadata.json не найден. Укажите путь через METADATA_JSON_PATH или поместите файл в parsed_metadata/."
  );
}

// ---------------------------------------------------------------------------
// Loading & indexing
// ---------------------------------------------------------------------------

/**
 * Извлекает «короткое имя» объекта из строки вида "Catalog.Номенклатура" → "Номенклатура".
 * Если точки нет — возвращает строку как есть.
 */
function shortName(fullRef: string): string {
  const dotIdx = fullRef.indexOf(".");
  return dotIdx >= 0 ? fullRef.substring(dotIdx + 1) : fullRef;
}

async function loadSubsystems(): Promise<SubsystemCache> {
  const jsonPath = resolveJsonPath();
  const raw = await readFile(jsonPath, "utf-8");
  const entries: RawMetadataEntry[] = JSON.parse(raw);

  const subsystemMap = new Map<string, SubsystemInfo>();
  const objectToSubsystems = new Map<string, string[]>();

  // 1. Собираем все подсистемы
  for (const entry of entries) {
    if (entry.object_type !== "Subsystem") continue;

    const info: SubsystemInfo = {
      name: entry.name,
      synonym: entry.synonym ?? entry.name,
      content: entry.content ?? [],
      children: entry.child_subsystems ?? [],
    };
    subsystemMap.set(entry.name, info);
  }

  // 2. Строим обратный индекс: объект → подсистемы
  for (const [subsystemName, info] of subsystemMap) {
    for (const ref of info.content) {
      const short = shortName(ref);

      // Индексируем и по полному имени ("Catalog.Номенклатура"), и по короткому ("Номенклатура")
      for (const key of [ref, short]) {
        const existing = objectToSubsystems.get(key);
        if (existing) {
          existing.push(subsystemName);
        } else {
          objectToSubsystems.set(key, [subsystemName]);
        }
      }
    }
  }

  // 3. Определяем top-level подсистемы (не являются child ни одной другой)
  const allChildren = new Set<string>();
  for (const info of subsystemMap.values()) {
    for (const child of info.children) {
      allChildren.add(child);
    }
  }

  const topLevelSubsystems = Array.from(subsystemMap.keys())
    .filter((name) => !allChildren.has(name))
    .sort();

  return { subsystemMap, objectToSubsystems, topLevelSubsystems };
}

/** Lazy-загрузка с кешированием. Потокобезопасна (один Promise). */
async function ensureLoaded(): Promise<SubsystemCache> {
  if (cache) return cache;
  if (!loadingPromise) {
    loadingPromise = loadSubsystems().then((result) => {
      cache = result;
      loadingPromise = null;
      return result;
    });
  }
  return loadingPromise;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Дерево подсистем верхнего уровня с количеством объектов.
 * Параметр `collectionName` зарезервирован для совместимости с интерфейсом tools
 * (данные всегда берутся из JSON).
 */
export async function getSubsystemTree(
  _collectionName?: string
): Promise<SubsystemTreeEntry[]> {
  const { subsystemMap, topLevelSubsystems } = await ensureLoaded();

  return topLevelSubsystems.map((name) => {
    const info = subsystemMap.get(name)!;
    return {
      name: info.name,
      synonym: info.synonym,
      objectCount: info.content.length,
      childCount: info.children.length,
    };
  });
}

/**
 * Содержимое подсистемы — список объектов.
 * При `recursive=true` рекурсивно включает объекты всех дочерних подсистем.
 */
export async function getSubsystemContent(
  name: string,
  recursive: boolean = false
): Promise<SubsystemContentResult | null> {
  const { subsystemMap } = await ensureLoaded();

  const info = subsystemMap.get(name);
  if (!info) return null;

  if (!recursive) {
    return {
      name: info.name,
      synonym: info.synonym,
      objects: [...info.content],
    };
  }

  // Рекурсивный сбор объектов из всех вложенных подсистем
  const allObjects = new Set<string>(info.content);
  const includedSubsystems: string[] = [];
  const visited = new Set<string>([name]);

  const queue = [...info.children];
  while (queue.length > 0) {
    const childName = queue.shift()!;
    if (visited.has(childName)) continue;
    visited.add(childName);

    const child = subsystemMap.get(childName);
    if (!child) continue;

    includedSubsystems.push(childName);
    for (const obj of child.content) {
      allObjects.add(obj);
    }
    for (const nested of child.children) {
      queue.push(nested);
    }
  }

  return {
    name: info.name,
    synonym: info.synonym,
    objects: Array.from(allObjects),
    includedSubsystems,
  };
}

/**
 * Поиск подсистем, содержащих указанный объект.
 * `objectName` может быть полным именем ("Catalog.Номенклатура") или коротким ("Номенклатура").
 */
export async function findObjectInSubsystems(
  objectName: string
): Promise<ObjectSubsystemsResult> {
  const { objectToSubsystems, subsystemMap } = await ensureLoaded();

  const subsystemNames = objectToSubsystems.get(objectName) ?? [];

  // Убираем дубликаты (объект мог попасть и по полному, и по короткому имени)
  const uniqueNames = [...new Set(subsystemNames)];

  return {
    objectName,
    subsystems: uniqueNames.map((n) => {
      const info = subsystemMap.get(n)!;
      return { name: n, synonym: info.synonym };
    }),
  };
}

/**
 * Сбрасывает кеш (полезно для тестов или перезагрузки данных).
 */
export function resetSubsystemCache(): void {
  cache = null;
  loadingPromise = null;
}
