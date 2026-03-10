import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { registerSearchMetadata } from "./tools/searchMetadata.js";
import { registerGetObjectDetails } from "./tools/getObjectDetails.js";
import { registerListObjectTypes } from "./tools/listObjectTypes.js";
import { registerSearchCode } from "./tools/searchCode.js";
import { registerOdataQuery } from "./tools/odataQuery.js";
import { registerRegisterBalances } from "./tools/registerBalances.js";
import { registerRegisterMovements } from "./tools/registerMovements.js";
import { registerDependencies } from "./tools/dependencies.js";
import { registerSubsystems } from "./tools/subsystems.js";
import { config } from "./config.js";

export function createMcpServer(getCollection: () => string): McpServer {
  const server = new McpServer({
    name: "mcp-1c-metadata",
    version: "0.3.0",
  });

  // Metadata tools (always available)
  registerSearchMetadata(server, getCollection);
  registerGetObjectDetails(server, getCollection);
  registerListObjectTypes(server, getCollection);
  registerSearchCode(server, getCollection);

  // Graph & navigation tools (always available)
  registerDependencies(server, getCollection);
  registerSubsystems(server, getCollection);

  // OData tools (available only when ODATA_URL is configured)
  if (config.odataUrl) {
    console.log(`OData tools enabled: ${config.odataUrl}`);
    registerOdataQuery(server);
    registerRegisterBalances(server);
    registerRegisterMovements(server);
  } else {
    console.log("OData tools disabled (ODATA_URL not set)");
  }

  return server;
}
