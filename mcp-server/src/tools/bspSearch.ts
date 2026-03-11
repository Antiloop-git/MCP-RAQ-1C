import { z } from "zod";
import { genericSearch } from "../services/qdrantService.js";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

export function registerBspSearch(server: McpServer) {
  server.tool(
    "1c_bsp_search",
    "Поиск по справке БСП (Библиотека стандартных подсистем). Возвращает документацию по подсистемам БСП.",
    {
      query: z.string().describe("Поисковый запрос (например: 'загрузка данных из файла', 'работа с файлами')"),
      limit: z.number().int().min(1).max(20).optional().default(5).describe("Количество результатов (по умолчанию 5)"),
    },
    async ({ query, limit }) => {
      try {
        const results = await genericSearch(query, "bsp_1c", { limit: limit ?? 5 });
        if (results.length === 0) {
          return { content: [{ type: "text" as const, text: `По запросу "${query}" в справке БСП ничего не найдено.` }] };
        }
        const lines = results.map((r, i) => {
          const p = r.payload;
          const subsystem = (p.subsystem as string) || "";
          const title = (p.title as string) || "Без заголовка";
          const content = ((p.content as string) || "").slice(0, 500);
          return `--- [${i + 1}] ${title} [${subsystem}] | score: ${r.score.toFixed(2)} ---\n${content}`;
        });
        return { content: [{ type: "text" as const, text: `Найдено ${results.length} раздел(ов) справки БСП по "${query}":\n\n${lines.join("\n\n")}` }] };
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return { content: [{ type: "text" as const, text: `Ошибка поиска по справке БСП: ${message}` }], isError: true };
      }
    }
  );
}
