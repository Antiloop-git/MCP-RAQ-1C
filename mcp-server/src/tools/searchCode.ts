import { z } from "zod";
import { codeSearch } from "../services/qdrantService.js";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

export function registerSearchCode(server: McpServer, _getCollection: () => string) {
    server.tool(
        "1c_code_search",
        "Поиск по исходному коду (BSL) конфигурации 1С. Возвращает фрагменты процедур/функций, соответствующих запросу. Используй для поиска логики бизнес-процессов, условий проведения, алгоритмов расчёта.",
        {
            query: z.string().describe("Поисковый запрос (например: 'движение на минус по складу', 'запись в регистр остатков')"),
            object_name: z
                .string()
                .optional()
                .describe("Фильтр по имени объекта (например: SS_РасходнаяНакладная)"),
            object_type: z
                .string()
                .optional()
                .describe("Фильтр по типу объекта (например: Document, AccumulationRegister)"),
            limit: z
                .number()
                .int()
                .min(1)
                .max(20)
                .optional()
                .default(5)
                .describe("Количество результатов (по умолчанию 5, макс 20)"),
        },
        async ({ query, object_name, object_type, limit }) => {
            try {
                const results = await codeSearch(query, {
                    objectName: object_name,
                    objectType: object_type,
                    limit: limit ?? 5,
                });

                if (results.length === 0) {
                    return {
                        content: [
                            {
                                type: "text" as const,
                                text: `По запросу "${query}" код не найден.`,
                            },
                        ],
                    };
                }

                const lines = results.map((r, i) => {
                    const header = `--- [${i + 1}] ${r.objectType}.${r.objectName} → ${r.procName} (score: ${r.score.toFixed(2)}) ---`;
                    const snippet = r.chunkText.slice(0, 600);
                    const ellipsis = r.chunkText.length > 600 ? "\n...[обрезано]" : "";
                    return `${header}\n${snippet}${ellipsis}`;
                });

                const text = `Найдено ${results.length} фрагмент(ов) кода по запросу "${query}":\n\n${lines.join("\n\n")}`;

                return {
                    content: [
                        { type: "text" as const, text },
                    ],
                };
            } catch (error) {
                const message = error instanceof Error ? error.message : String(error);
                return {
                    content: [
                        {
                            type: "text" as const,
                            text: `Ошибка поиска по коду: ${message}`,
                        },
                    ],
                    isError: true,
                };
            }
        }
    );
}
