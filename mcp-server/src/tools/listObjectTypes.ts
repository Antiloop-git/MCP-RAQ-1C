import { getObjectTypeStats } from "../services/qdrantService.js";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

export function registerListObjectTypes(server: McpServer, getCollection: () => string) {
  server.tool(
    "1c_metadata_types",
    "Получить статистику по типам объектов метаданных 1С в конфигурации: тип, русское название, количество.",
    {},
    async () => {
      try {
        const stats = await getObjectTypeStats(getCollection());

        if (stats.length === 0) {
          return {
            content: [
              {
                type: "text" as const,
                text: "Коллекция пуста или недоступна.",
              },
            ],
          };
        }

        const total = stats.reduce((sum, s) => sum + s.count, 0);
        const lines = stats.map(
          (s) => `${s.type}\t${s.typeRu}\t${s.count}`
        );

        const text = [
          `Типы объектов метаданных (всего ${total}):`,
          "",
          "Тип\tРусское имя\tКоличество",
          ...lines,
        ].join("\n");

        return {
          content: [{ type: "text" as const, text }],
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
