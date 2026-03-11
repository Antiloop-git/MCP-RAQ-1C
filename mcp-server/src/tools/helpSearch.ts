import { z } from "zod";
import { genericSearch } from "../services/qdrantService.js";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

export function registerHelpSearch(server: McpServer) {
  server.tool(
    "1c_help_search",
    "Поиск по справке платформы 1С:Предприятие 8.3. Возвращает релевантные разделы документации по ключевым словам.",
    {
      query: z.string().describe("Поисковый запрос (например: 'запрос к регистру накопления', 'условное оформление')"),
      limit: z.number().int().min(1).max(20).optional().default(5).describe("Количество результатов (по умолчанию 5)"),
    },
    async ({ query, limit }) => {
      try {
        const results = await genericSearch(query, "help_1c", { limit: limit ?? 5 });
        if (results.length === 0) {
          return { content: [{ type: "text" as const, text: `По запросу "${query}" в справке платформы ничего не найдено.` }] };
        }
        const lines = results.map((r, i) => {
          const p = r.payload;
          const title = (p.title as string) || "Без заголовка";
          const section = (p.section as string) || "";
          const content = ((p.content as string) || "").slice(0, 500);
          return `--- [${i + 1}] ${title} (${section}) | score: ${r.score.toFixed(2)} ---\n${content}`;
        });
        return { content: [{ type: "text" as const, text: `Найдено ${results.length} раздел(ов) справки по "${query}":\n\n${lines.join("\n\n")}` }] };
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return { content: [{ type: "text" as const, text: `Ошибка поиска по справке: ${message}` }], isError: true };
      }
    }
  );
}
