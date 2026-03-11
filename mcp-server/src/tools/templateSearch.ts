import { z } from "zod";
import { genericSearch } from "../services/qdrantService.js";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

const CATEGORY_VALUES = [
  "запросы",
  "регистры",
  "справочники",
  "документы",
  "формы",
  "обмен",
  "права",
  "общие",
  "строки",
  "даты",
  "коллекции",
  "файлы",
  "транзакции",
  "интерфейс",
  "web",
  "печать",
] as const;

export function registerTemplateSearch(server: McpServer) {
  server.tool(
    "1c_templates",
    "Поиск шаблонов и сниппетов кода 1С. Возвращает готовые примеры кода по запросу (запросы, регистры, формы, обмен данными и др.).",
    {
      query: z.string().describe("Поисковый запрос (например: 'получить остатки по складу', 'загрузить из Excel')"),
      category: z.enum(CATEGORY_VALUES).optional().describe(
        "Категория шаблона: запросы, регистры, справочники, документы, формы, обмен, права, общие, строки, даты, коллекции, файлы, транзакции, интерфейс, web, печать"
      ),
      limit: z.number().int().min(1).max(20).optional().default(5).describe("Количество результатов (по умолчанию 5)"),
    },
    async ({ query, category, limit }) => {
      try {
        const filter = category
          ? { must: [{ key: "category", match: { value: category } }] }
          : undefined;

        const results = await genericSearch(query, "templates_1c", { limit: limit ?? 5, filter });
        if (results.length === 0) {
          const categoryMsg = category ? ` в категории "${category}"` : "";
          return { content: [{ type: "text" as const, text: `По запросу "${query}"${categoryMsg} шаблоны не найдены.` }] };
        }
        const lines = results.map((r, i) => {
          const p = r.payload;
          const title = (p.title as string) || "Без заголовка";
          const cat = (p.category as string) || "";
          const tags = Array.isArray(p.tags) ? (p.tags as string[]).join(", ") : ((p.tags as string) || "");
          const description = (p.description as string) || "";
          const code = (p.code as string) || "";
          const header = `--- [${i + 1}] ${title} | категория: ${cat} | теги: ${tags} | score: ${r.score.toFixed(2)} ---`;
          const body = [description && `Описание: ${description}`, code && `Код:\n${code}`]
            .filter(Boolean)
            .join("\n");
          return `${header}\n${body}`;
        });
        return { content: [{ type: "text" as const, text: `Найдено ${results.length} шаблон(ов) по "${query}":\n\n${lines.join("\n\n")}` }] };
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return { content: [{ type: "text" as const, text: `Ошибка поиска шаблонов: ${message}` }], isError: true };
      }
    }
  );
}
