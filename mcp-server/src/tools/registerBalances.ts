import { z } from "zod";
import { odataGet } from "../services/odataService.js";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

/**
 * Tool to query accumulation register balances from 1C via OData.
 * Primary use case: finding negative stock balances.
 *
 * 1C OData virtual tables:
 *   Balance — only for "остаточные" registers (e.g. УчетПартий)
 *   Turnovers — for both types
 *   BalanceAndTurnovers — only for "остаточные"
 *
 * Called via: AccumulationRegister_Name/Balance(Condition='...')
 * Or as EntitySet: AccumulationRegister_Name_RecordType with $filter
 */
export function registerRegisterBalances(server: McpServer) {
  server.tool(
    "1c_register_balances",
    `Получить остатки или обороты регистра накопления 1С.

Доступные регистры:
  УчетПартий — ОСТАТОЧНЫЙ: Balance(КоличествоBalance, СуммаБезНДСBalance), Turnovers, BalanceAndTurnovers
  ДвижениеТМЦ — ОБОРОТНЫЙ: только Turnovers (КоличествоTurnover, СуммаTurnover, ПрибыльTurnover)

Виды таблиц (table_type):
  Balance — остатки на дату (только остаточные регистры)
  Turnovers — обороты за период
  BalanceAndTurnovers — остатки + обороты (только остаточные)
  RecordType — записи движений (все регистры)

Для поиска отрицательных остатков используйте УчетПартий + Balance + фильтр КоличествоBalance lt 0.`,
    {
      register_name: z
        .string()
        .describe(
          "Имя регистра накопления: УчетПартий (остаточный, есть Balance) или ДвижениеТМЦ (оборотный, только Turnovers)"
        ),
      table_type: z
        .enum(["Balance", "Turnovers", "BalanceAndTurnovers", "RecordType"])
        .default("RecordType")
        .describe("Тип виртуальной таблицы"),
      filter: z
        .string()
        .optional()
        .describe(
          "OData $filter, например: КоличествоBalance lt 0"
        ),
      select: z
        .string()
        .optional()
        .describe(
          "Поля через запятую ($select)"
        ),
      top: z
        .number()
        .int()
        .min(1)
        .max(500)
        .optional()
        .default(50)
        .describe("Максимум записей, по умолчанию 50"),
      condition: z
        .string()
        .optional()
        .describe(
          "Параметры виртуальной таблицы (Condition для Balance/Turnovers)"
        ),
    },
    async ({ register_name, table_type, filter, select, top, condition }) => {
      try {
        // Virtual tables (Balance, Turnovers, BalanceAndTurnovers) are FunctionImports:
        //   AccumulationRegister_Name/Balance
        // RecordType is an EntitySet:
        //   AccumulationRegister_Name_RecordType
        const entitySet =
          table_type === "RecordType"
            ? `AccumulationRegister_${register_name}_RecordType`
            : `AccumulationRegister_${register_name}/${table_type}`;

        const params: Record<string, string> = {};
        if (filter) params["$filter"] = filter;
        if (select) params["$select"] = select;
        if (top) params["$top"] = String(top);
        if (condition) params["Condition"] = condition;

        const results = await odataGet(entitySet, params);

        if (results.length === 0) {
          return {
            content: [
              {
                type: "text" as const,
                text: `Регистр ${register_name} (${table_type}): данных по фильтру не найдено.${filter ? ` Фильтр: ${filter}` : ""}`,
              },
            ],
          };
        }

        // Filter out navigation links for cleaner output
        const keys = Object.keys(results[0]!).filter(
          (k) => !k.endsWith("@navigationLinkUrl")
        );
        const header = keys.join("\t");
        const rows = results.map((row) =>
          keys.map((k) => formatVal(row[k])).join("\t")
        );

        const negativeCount = countNegativeBalances(results);
        const summary = negativeCount > 0
          ? `⚠ Найдено ${negativeCount} позиций с отрицательными остатками`
          : table_type === "Balance"
            ? "Все остатки неотрицательные"
            : "";

        const text = `${register_name} (${table_type}): ${results.length} записей\n${summary}\n\n${header}\n${rows.join("\n")}`;

        return {
          content: [{ type: "text" as const, text }],
        };
      } catch (error) {
        const message =
          error instanceof Error ? error.message : String(error);
        return {
          content: [
            { type: "text" as const, text: `Ошибка получения данных регистра: ${message}` },
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

function countNegativeBalances(
  rows: Record<string, unknown>[]
): number {
  let count = 0;
  for (const row of rows) {
    for (const [key, val] of Object.entries(row)) {
      if (key.endsWith("Balance") && typeof val === "number" && val < 0) {
        count++;
        break;
      }
    }
  }
  return count;
}
