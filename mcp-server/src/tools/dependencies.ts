import { z } from "zod";
import { getDependencies } from "../services/graphService.js";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

/**
 * MCP tool: 1c_dependencies
 * Shows document↔register dependencies from the 1C configuration.
 */
export function registerDependencies(
  server: McpServer,
  getCollection: () => string,
) {
  server.tool(
    "1c_dependencies",
    `Показать зависимости между документами и регистрами конфигурации 1С.
forward — в какие регистры пишет документ.
reverse — какие документы пишут в регистр.
all — все связи объекта в обоих направлениях.
Используйте для анализа влияния изменений: «что затронется, если изменить объект X?»`,
    {
      name: z
        .string()
        .describe(
          "Имя объекта (документа или регистра), например: ПриходнаяНакладная, УчетПартий, ДвижениеТМЦ",
        ),
      direction: z
        .enum(["forward", "reverse", "all"])
        .default("all")
        .describe(
          "forward — документ→регистры, reverse — регистр→документы, all — оба направления",
        ),
    },
    async ({ name, direction }) => {
      try {
        const result = await getDependencies(
          name,
          direction,
          getCollection(),
        );

        if (result.relations.length === 0) {
          return {
            content: [
              {
                type: "text" as const,
                text: `Объект «${name}» не найден в графе зависимостей (direction=${direction}).\nВозможно, это не документ и не регистр накопления, или у документа нет движений.\nИспользуйте 1c_metadata_search для поиска объекта.`,
              },
            ],
          };
        }

        // Group relations by direction
        const forward = result.relations.filter(
          (r) => r.direction === "forward",
        );
        const reverse = result.relations.filter(
          (r) => r.direction === "reverse",
        );

        const lines: string[] = [];
        lines.push(`Зависимости объекта «${name}»:\n`);

        if (forward.length > 0) {
          lines.push(
            `Документ → Регистры (${forward.length}):`,
          );
          for (const r of forward) {
            lines.push(`  • ${r.name}`);
          }
          lines.push("");
        }

        if (reverse.length > 0) {
          lines.push(
            `Регистр ← Документы (${reverse.length}):`,
          );
          for (const r of reverse) {
            lines.push(`  • ${r.name}`);
          }
          lines.push("");
        }

        lines.push(
          `Итого: ${forward.length} регистров, ${reverse.length} документов`,
        );

        return {
          content: [{ type: "text" as const, text: lines.join("\n") }],
        };
      } catch (error) {
        const message =
          error instanceof Error ? error.message : String(error);
        return {
          content: [
            {
              type: "text" as const,
              text: `Ошибка получения зависимостей: ${message}`,
            },
          ],
          isError: true,
        };
      }
    },
  );
}
