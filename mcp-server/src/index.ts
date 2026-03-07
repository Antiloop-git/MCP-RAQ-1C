import express from "express";
import { randomUUID } from "node:crypto";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { createMcpServer } from "./server.js";
import { config } from "./config.js";

const app = express();
app.use(express.json());

// --- Health check ---
app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

// --- Streamable HTTP transport (POST /mcp, GET /mcp, DELETE /mcp) ---
// Session management for Streamable HTTP
const streamableTransports = new Map<string, { transport: StreamableHTTPServerTransport; createdAt: number }>();

// Cleanup stale sessions every 10 minutes (TTL: 30 min)
const SESSION_TTL_MS = 30 * 60 * 1000;
setInterval(() => {
  const now = Date.now();
  for (const [id, entry] of streamableTransports) {
    if (now - entry.createdAt > SESSION_TTL_MS) {
      streamableTransports.delete(id);
    }
  }
}, 10 * 60 * 1000);

app.post("/mcp", async (req, res) => {
  const sessionId = req.headers["mcp-session-id"] as string | undefined;
  let transport: StreamableHTTPServerTransport;

  if (sessionId && streamableTransports.has(sessionId)) {
    transport = streamableTransports.get(sessionId)!.transport;
  } else if (!sessionId && isInitializeRequest(req.body)) {
    const collectionName =
      (req.headers["x-collection-name"] as string) || config.defaultCollection;
    const getCollection = () => collectionName;
    const server = createMcpServer(getCollection);

    transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => randomUUID(),
      onsessioninitialized: (id) => {
        streamableTransports.set(id, { transport, createdAt: Date.now() });
      },
    });

    transport.onclose = () => {
      const id = transport.sessionId;
      if (id) streamableTransports.delete(id);
    };

    await server.connect(transport);
  } else {
    res.status(400).json({ error: "Bad request: missing or invalid session" });
    return;
  }

  await transport.handleRequest(req, res, req.body);
});

app.get("/mcp", async (req, res) => {
  const sessionId = req.headers["mcp-session-id"] as string | undefined;
  if (!sessionId || !streamableTransports.has(sessionId)) {
    res.status(400).json({ error: "Invalid or missing session ID" });
    return;
  }
  const { transport } = streamableTransports.get(sessionId)!;
  await transport.handleRequest(req, res);
});

app.delete("/mcp", async (req, res) => {
  const sessionId = req.headers["mcp-session-id"] as string | undefined;
  if (!sessionId || !streamableTransports.has(sessionId)) {
    res.status(400).json({ error: "Invalid or missing session ID" });
    return;
  }
  const { transport } = streamableTransports.get(sessionId)!;
  await transport.handleRequest(req, res);
});

// --- SSE transport (GET /sse + POST /messages) for backward compatibility ---
const sseTransports = new Map<string, { transport: SSEServerTransport; createdAt: number }>();

// Cleanup stale SSE sessions every 10 minutes (TTL: 30 min)
setInterval(() => {
  const now = Date.now();
  for (const [id, entry] of sseTransports) {
    if (now - entry.createdAt > SESSION_TTL_MS) {
      sseTransports.delete(id);
    }
  }
}, 10 * 60 * 1000);

app.get("/sse", async (req, res) => {
  const collectionName =
    (req.headers["x-collection-name"] as string) || config.defaultCollection;
  const getCollection = () => collectionName;
  const server = createMcpServer(getCollection);

  const transport = new SSEServerTransport("/messages", res);
  sseTransports.set(transport.sessionId, { transport, createdAt: Date.now() });

  transport.onclose = () => {
    sseTransports.delete(transport.sessionId);
  };

  await server.connect(transport);
});

app.post("/messages", async (req, res) => {
  const sessionId = req.query.sessionId as string | undefined;
  if (!sessionId || !sseTransports.has(sessionId)) {
    res.status(400).json({ error: "Invalid or missing session ID" });
    return;
  }
  const { transport } = sseTransports.get(sessionId)!;
  await transport.handlePostMessage(req, res, req.body);
});

// --- Helper ---
function isInitializeRequest(body: unknown): boolean {
  if (Array.isArray(body)) {
    return body.some(
      (m) => typeof m === "object" && m !== null && (m as Record<string, unknown>).method === "initialize"
    );
  }
  if (typeof body === "object" && body !== null) {
    return (body as Record<string, unknown>).method === "initialize";
  }
  return false;
}

// --- Start ---
app.listen(config.port, config.host, () => {
  console.log(`MCP Server listening on http://${config.host}:${config.port}`);
  console.log(`  Streamable HTTP: POST/GET /mcp`);
  console.log(`  SSE: GET /sse`);
  console.log(`  Health: GET /health`);
  console.log(`  Default collection: ${config.defaultCollection}`);
});
