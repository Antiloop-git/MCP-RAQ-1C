import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { registerSearchMetadata } from "./tools/searchMetadata.js";
import { registerGetObjectDetails } from "./tools/getObjectDetails.js";
import { registerListObjectTypes } from "./tools/listObjectTypes.js";
import { registerSearchCode } from "./tools/searchCode.js";

export function createMcpServer(getCollection: () => string): McpServer {
  const server = new McpServer({
    name: "mcp-1c-metadata",
    version: "0.1.0",
  });

  registerSearchMetadata(server, getCollection);
  registerGetObjectDetails(server, getCollection);
  registerListObjectTypes(server, getCollection);
  registerSearchCode(server, getCollection);

  return server;
}
