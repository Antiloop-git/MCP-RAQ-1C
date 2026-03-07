import { z } from "zod";
import { hybridSearch } from "../services/qdrantService.js";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

const objectTypes = [
  "Catalog",
  "Document",
  "AccumulationRegister",
  "InformationRegister",
  "AccountingRegister",
  "Enum",
  "Constant",
  "DataProcessor",
  "Report",
  "ChartOfAccounts",
  "ChartOfCharacteristicTypes",
  "ExchangePlan",
  "BusinessProcess",
  "Task",
  "DefinedType",
  "DocumentJournal",
  "CommonModule",
  "Subsystem",
  "EventSubscription",
  "ScheduledJob",
  "HTTPService",
  "WebService",
  "CommonCommand",
  "FunctionalOption",
  "CommonAttribute",
  "Role",
  "XDTOPackage",
  "SessionParameter",
  "CommonForm",
  "ExternalDataSource",
  "FilterCriterion",
  "Sequence",
  "FunctionalOptionsParameter",
  "DocumentNumerator",
  "CommandGroup",
  "SettingsStorage",
] as const;

export function registerSearchMetadata(server: McpServer, getCollection: () => string) {
  server.tool(
    "1c_metadata_search",
    "Поиск объектов метаданных 1С по текстовому запросу. Возвращает компактный список (имя, синоним, тип). Для полного описания используйте 1c_metadata_details.",
    {
      query: z.string().describe("Поисковый запрос"),
      object_type: z
        .enum(objectTypes)
        .optional()
        .describe("Фильтр по типу объекта"),
      limit: z
        .number()
        .int()
        .min(1)
        .max(50)
        .optional()
        .default(10)
        .describe("Количество результатов (по умолчанию 10, макс 50)"),
    },
    async ({ query, object_type, limit }) => {
      try {
        const results = await hybridSearch(query, {
          objectType: object_type,
          limit: limit ?? 10,
          collectionName: getCollection(),
        });

        if (results.length === 0) {
          return {
            content: [
              {
                type: "text" as const,
                text: `По запросу "${query}" ничего не найдено.`,
              },
            ],
          };
        }

        const lines = results.map(
          (r, i) =>
            `${i + 1}. ${r.name} | ${r.synonym} | ${r.objectTypeRu} | score: ${r.score.toFixed(2)}`
        );

        const text = `Найдено ${results.length} объекта(ов) по запросу "${query}":\n\n${lines.join("\n")}`;

        return {
          content: [
            { type: "text" as const, text },
            {
              type: "resource" as const,
              resource: {
                uri: `metadata://search?q=${encodeURIComponent(query)}`,
                mimeType: "application/json",
                text: JSON.stringify(results, null, 2),
              },
            },
          ],
        };
      } catch (error) {
        const message =
          error instanceof Error ? error.message : String(error);
        return {
          content: [
            {
              type: "text" as const,
              text: `Ошибка поиска: ${message}`,
            },
          ],
          isError: true,
        };
      }
    }
  );
}
