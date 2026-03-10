import { z } from "zod";
import { odataGet, buildEntitySet } from "../services/odataService.js";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

/**
 * Tool to query register movements (records) from 1C via OData.
 * Use case: investigate what documents caused negative balances.
 */
export function registerRegisterMovements(server: McpServer) {
  server.tool(
    "1c_register_movements",
    `Получить движения (записи) регистра накопления 1С за период. Показывает какие документы создали приход/расход.
Используйте для анализа причин отрицательных остатков — смотрите поле Recorder (документ-регистратор).
Ключевые регистры:
  ДвижениеТМЦ — движение товаров (Приход/Расход)
  УчетПартий — партионный учёт
  Реализация — реализация товаров
  Отгрузка — отгрузка`,
    {
      register_name: z
        .string()
        .describe("Имя регистра накопления, например: ДвижениеТМЦ"),
      filter: z
        .string()
        .describe(
          "OData $filter — обязательно для ограничения выборки. Пример: Period ge datetime'2025-01-01T00:00:00' and Period le datetime'2025-01-31T23:59:59' and Номенклатура_Key eq guid'...'"
        ),
      select: z
        .string()
        .optional()
        .describe(
          "Поля через запятую, например: Period,Recorder,RecordType,Номенклатура,Склад,Количество"
        ),
      top: z
        .number()
        .int()
        .min(1)
        .max(500)
        .optional()
        .default(100)
        .describe("Максимум записей, по умолчанию 100"),
      orderby: z
        .string()
        .optional()
        .default("Period desc")
        .describe("Сортировка, по умолчанию: Period desc"),
    },
    async ({ register_name, filter, select, top, orderby }) => {
      try {
        // Movements = base entity set (no suffix)
        const entitySet = buildEntitySet(
          "AccumulationRegister",
          register_name
        );

        const params: Record<string, string> = {
          "$filter": filter,
        };
        if (select) params["$select"] = select;
        if (top) params["$top"] = String(top);
        if (orderby) params["$orderby"] = orderby;

        const results = await odataGet(entitySet, params);

        if (results.length === 0) {
          return {
            content: [
              {
                type: "text" as const,
                text: `Регистр ${register_name}: движений по фильтру не найдено.\nФильтр: ${filter}`,
              },
            ],
          };
        }

        // Format as TSV
        const keys = Object.keys(results[0]!);
        const header = keys.join("\t");
        const rows = results.map((row) =>
          keys.map((k) => formatVal(row[k])).join("\t")
        );

        // Summarize by RecordType if available
        const summary = summarizeMovements(results);

        const text = `Движения ${register_name}: ${results.length} записей\n${summary}\n\n${header}\n${rows.join("\n")}`;

        return {
          content: [{ type: "text" as const, text }],
        };
      } catch (error) {
        const message =
          error instanceof Error ? error.message : String(error);
        return {
          content: [
            {
              type: "text" as const,
              text: `Ошибка получения движений: ${message}`,
            },
          ],
          isError: true,
        };
      }
    }
  );
}

function formatVal(val: unknown): string {
  if (val === null || val === undefined) return "";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

function summarizeMovements(rows: Record<string, unknown>[]): string {
  let income = 0;
  let expense = 0;
  for (const row of rows) {
    const rt = row["RecordType"];
    if (rt === "Receipt" || rt === "Приход") income++;
    else if (rt === "Expense" || rt === "Расход") expense++;
  }
  if (income === 0 && expense === 0) return "";
  return `Приход: ${income}, Расход: ${expense}`;
}
