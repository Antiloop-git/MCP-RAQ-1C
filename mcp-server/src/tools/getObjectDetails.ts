import { z } from "zod";
import { getObjectByName, hybridSearch } from "../services/qdrantService.js";
import type { MetadataDetails } from "../types/metadata.js";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

function formatDetails(obj: MetadataDetails): string {
  const lines: string[] = [
    `Объект: ${obj.object_name}`,
    `Тип: ${obj.object_type_ru}`,
    `Синоним: ${obj.synonym}`,
  ];

  if (obj.attributes.length > 0) {
    lines.push("", "Реквизиты:");
    for (const attr of obj.attributes) {
      lines.push(`  - ${attr}`);
    }
  }

  if (obj.tabular_sections.length > 0) {
    lines.push("", "Табличные части:");
    for (const ts of obj.tabular_sections) {
      lines.push(ts);
    }
  }

  if (obj.register_records.length > 0) {
    lines.push("", "Движения регистров:");
    for (const reg of obj.register_records) {
      lines.push(reg);
    }
  }

  if (obj.description) {
    lines.push("", "--- Полное описание ---", obj.description);
  }

  return lines.join("\n");
}

export function registerGetObjectDetails(server: McpServer, getCollection: () => string) {
  server.tool(
    "1c_metadata_details",
    "Получить полное описание объекта метаданных 1С по техническому имени. Возвращает реквизиты, табличные части, движения регистров в TSV-формате.",
    {
      name: z.string().describe("Техническое имя объекта (например, SS_ЗаказКлиента)"),
      objectType: z.string().optional().describe("Тип объекта на английском (Catalog, Document, InformationRegister и т.д.). Уточняет поиск при совпадении имён."),
    },
    async ({ name, objectType }) => {
      try {
        const obj = await getObjectByName(name, getCollection(), objectType);

        if (obj) {
          return {
            content: [
              { type: "text" as const, text: formatDetails(obj) },
            ],
          };
        }

        // Object not found — feedback with similar results
        let feedback = `Объект '${name}' не найден.`;
        try {
          const similar = await hybridSearch(name, {
            limit: 3,
            collectionName: getCollection(),
          });
          if (similar.length > 0) {
            const suggestions = similar
              .map((r) => `  - ${r.name} (${r.synonym})`)
              .join("\n");
            feedback += ` Возможно, вы имели в виду:\n${suggestions}`;
          }
        } catch {
          // Embedding service may be unavailable — skip suggestions
        }

        return {
          content: [{ type: "text" as const, text: feedback }],
        };
      } catch (error) {
        const message =
          error instanceof Error ? error.message : String(error);
        return {
          content: [
            { type: "text" as const, text: `Ошибка: ${message}` },
          ],
          isError: true,
        };
      }
    }
  );
}
