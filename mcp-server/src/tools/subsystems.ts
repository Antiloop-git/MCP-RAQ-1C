import { z } from "zod";
import {
  getSubsystemTree,
  getSubsystemContent,
  findObjectInSubsystems,
} from "../services/subsystemService.js";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

/**
 * MCP tool: 1c_subsystems
 * Navigation through the subsystem tree of a 1C configuration.
 */
export function registerSubsystems(
  server: McpServer,
  _getCollection: () => string,
) {
  server.tool(
    "1c_subsystems",
    `Навигация по подсистемам конфигурации 1С (бизнес-модулям).
tree — дерево подсистем верхнего уровня (49 шт).
content — объекты конкретной подсистемы (документы, справочники, регистры и т.д.).
find — в каких подсистемах находится указанный объект.
Подсистемы помогают понять бизнес-структуру конфигурации и роль каждого объекта.`,
    {
      action: z
        .enum(["tree", "content", "find"])
        .describe(
          "tree — дерево верхнего уровня, content — объекты подсистемы, find — поиск объекта в подсистемах",
        ),
      name: z
        .string()
        .optional()
        .describe(
          "Имя подсистемы (для content) или объекта (для find). Обязательно для content и find.",
        ),
      recursive: z
        .boolean()
        .default(false)
        .describe(
          "Для content: включать объекты вложенных подсистем (по умолчанию false)",
        ),
    },
    async ({ action, name, recursive }) => {
      try {
        if (action === "tree") {
          return await handleTree();
        }

        if (!name) {
          return {
            content: [
              {
                type: "text" as const,
                text: `Параметр name обязателен для action="${action}". Укажите имя подсистемы или объекта.`,
              },
            ],
            isError: true,
          };
        }

        if (action === "content") {
          return await handleContent(name, recursive);
        }

        // action === "find"
        return await handleFind(name);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : String(error);
        return {
          content: [
            {
              type: "text" as const,
              text: `Ошибка работы с подсистемами: ${message}`,
            },
          ],
          isError: true,
        };
      }
    },
  );
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

async function handleTree() {
  const tree = await getSubsystemTree();

  if (tree.length === 0) {
    return {
      content: [
        { type: "text" as const, text: "Подсистемы не найдены." },
      ],
    };
  }

  const lines = tree.map(
    (s, i) =>
      `${i + 1}. ${s.name} (${s.synonym}) — ${s.objectCount} объектов${s.childCount > 0 ? `, ${s.childCount} вложенных` : ""}`,
  );

  return {
    content: [
      {
        type: "text" as const,
        text: `Подсистемы верхнего уровня (${tree.length}):\n\n${lines.join("\n")}`,
      },
    ],
  };
}

async function handleContent(name: string, recursive: boolean) {
  const result = await getSubsystemContent(name, recursive);

  if (!result) {
    return {
      content: [
        {
          type: "text" as const,
          text: `Подсистема «${name}» не найдена. Используйте action="tree" для просмотра доступных подсистем.`,
        },
      ],
    };
  }

  const lines: string[] = [];
  lines.push(
    `Подсистема «${result.name}» (${result.synonym}): ${result.objects.length} объектов${recursive ? " (рекурсивно)" : ""}\n`,
  );

  if (
    result.includedSubsystems &&
    result.includedSubsystems.length > 0
  ) {
    lines.push(
      `Включённые подсистемы: ${result.includedSubsystems.join(", ")}\n`,
    );
  }

  for (const obj of result.objects) {
    lines.push(`  • ${obj}`);
  }

  return {
    content: [{ type: "text" as const, text: lines.join("\n") }],
  };
}

async function handleFind(name: string) {
  const result = await findObjectInSubsystems(name);

  if (result.subsystems.length === 0) {
    return {
      content: [
        {
          type: "text" as const,
          text: `Объект «${name}» не найден ни в одной подсистеме. Проверьте имя через 1c_metadata_search.`,
        },
      ],
    };
  }

  const lines = result.subsystems.map(
    (s, i) => `${i + 1}. ${s.name} (${s.synonym})`,
  );

  return {
    content: [
      {
        type: "text" as const,
        text: `Объект «${name}» найден в подсистемах (${result.subsystems.length}):\n\n${lines.join("\n")}`,
      },
    ],
  };
}
