import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { config } from "../config.js";

const SEVERITY_LABELS: Record<number, string> = {
    1: "Ошибка",
    2: "Предупреждение",
    3: "Информация",
    4: "Подсказка",
};

interface Diagnostic {
    range: {
        start: { line: number; character: number };
        end: { line: number; character: number };
    };
    severity: number;
    code: string;
    message: string;
}

interface AnalyzeResponse {
    diagnostics: Diagnostic[];
    file_analyzed: string;
}

export function registerSyntaxCheck(server: McpServer) {
    server.tool(
        "1c_syntax_check",
        "Проверка синтаксиса BSL-кода (1С) через BSL Language Server. Принимает код на языке 1С, возвращает список ошибок и предупреждений.",
        {
            code: z.string().describe("BSL-код (1С) для проверки синтаксиса"),
        },
        async ({ code }) => {
            try {
                const response = await fetch(`${config.bslLsUrl}/analyze`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code }),
                });

                if (!response.ok) {
                    throw new Error(`BSL Language Server вернул статус ${response.status}`);
                }

                const data = (await response.json()) as AnalyzeResponse;
                const diagnostics = data.diagnostics ?? [];

                if (diagnostics.length === 0) {
                    return {
                        content: [{ type: "text" as const, text: "Синтаксических ошибок не найдено." }],
                    };
                }

                const lines = diagnostics.map((d) => {
                    const line = d.range.start.line + 1;
                    const severity = SEVERITY_LABELS[d.severity] ?? `Severity(${d.severity})`;
                    return `Строка ${line}: [${severity}] ${d.code} — ${d.message}`;
                });

                const text = `Найдено диагностик: ${diagnostics.length}\n\n${lines.join("\n")}`;

                return {
                    content: [{ type: "text" as const, text }],
                };
            } catch (error) {
                const message = error instanceof Error ? error.message : String(error);
                return {
                    content: [{ type: "text" as const, text: `Ошибка: ${message}` }],
                    isError: true,
                };
            }
        }
    );
}
