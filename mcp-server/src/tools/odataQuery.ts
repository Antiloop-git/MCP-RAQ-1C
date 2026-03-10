import { z } from "zod";
import { odataGet, buildEntitySet, odataHealthCheck } from "../services/odataService.js";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

/**
 * Universal OData query tool for 1C.
 * Allows LLM agents to query any published OData entity with filters.
 */
export function registerOdataQuery(server: McpServer) {
  server.tool(
    "1c_odata_query",
    `Универсальный запрос к OData-интерфейсу 1С. Позволяет читать данные справочников, документов, регистров.
Примеры entity_set:
  Catalog_Номенклатура — справочник
  Document_РеализацияТоваровУслуг — документ
  AccumulationRegister_ДвижениеТМЦ — движения регистра
  AccumulationRegister_ДвижениеТМЦ_Balance — остатки
  AccumulationRegister_ДвижениеТМЦ_Turnovers — обороты
  InformationRegister_ЦеныНоменклатуры_SliceLast — срез последних
Используйте 1c_metadata_search, чтобы узнать точные имена объектов.`,
    {
      entity_set: z
        .string()
        .describe(
          "Имя набора данных OData, например: Catalog_Номенклатура, AccumulationRegister_ДвижениеТМЦ_Balance"
        ),
      filter: z
        .string()
        .optional()
        .describe(
          'OData $filter, например: НоменклатураKey eq guid\'...\' or КоличествоBalance lt 0'
        ),
      select: z
        .string()
        .optional()
        .describe(
          "Список полей через запятую ($select), например: Номенклатура,Склад,КоличествоBalance"
        ),
      top: z
        .number()
        .int()
        .min(1)
        .max(1000)
        .optional()
        .default(100)
        .describe("Максимум записей ($top), по умолчанию 100"),
      orderby: z
        .string()
        .optional()
        .describe("Сортировка ($orderby), например: Period desc"),
    },
    async ({ entity_set, filter, select, top, orderby }) => {
      try {
        const params: Record<string, string> = {};
        if (filter) params["$filter"] = filter;
        if (select) params["$select"] = select;
        if (top) params["$top"] = String(top);
        if (orderby) params["$orderby"] = orderby;

        const results = await odataGet(entity_set, params);

        if (results.length === 0) {
          return {
            content: [
              {
                type: "text" as const,
                text: `Запрос к ${entity_set} вернул 0 записей.${filter ? ` Фильтр: ${filter}` : ""}`,
              },
            ],
          };
        }

        // Format as TSV for token efficiency
        const keys = Object.keys(results[0]!);
        const header = keys.join("\t");
        const rows = results.map((row) =>
          keys.map((k) => formatValue(row[k])).join("\t")
        );

        const text = `${entity_set}: ${results.length} записей\n\n${header}\n${rows.join("\n")}`;

        return {
          content: [{ type: "text" as const, text }],
        };
      } catch (error) {
        const message =
          error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: "text" as const, text: `Ошибка OData: ${message}` }],
          isError: true,
        };
      }
    }
  );
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return "";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}
