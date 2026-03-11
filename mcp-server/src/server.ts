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
import { registerSyntaxCheck } from "./tools/syntaxCheck.js";
import { registerHelpSearch } from "./tools/helpSearch.js";
import { registerBspSearch } from "./tools/bspSearch.js";
import { registerTemplateSearch } from "./tools/templateSearch.js";
import { config } from "./config.js";

export function createMcpServer(getCollection: () => string): McpServer {
  const server = new McpServer({
    name: "mcp-1c-metadata",
    version: "0.4.0",
  });

  // Metadata tools (always available)
  registerSearchMetadata(server, getCollection);
  registerGetObjectDetails(server, getCollection);
  registerListObjectTypes(server, getCollection);
  registerSearchCode(server, getCollection);

  // Graph & navigation tools (always available)
  registerDependencies(server, getCollection);
  registerSubsystems(server, getCollection);

  // Dev tools: help, BSP, templates (always available — search fails gracefully if collection empty)
  registerHelpSearch(server);
  registerBspSearch(server);
  registerTemplateSearch(server);

  // BSL Language Server (available only when BSL_LS_URL is configured)
  if (config.bslLsUrl) {
    console.log(`BSL LS tools enabled: ${config.bslLsUrl}`);
    registerSyntaxCheck(server);
  } else {
    console.log("BSL LS tools disabled (BSL_LS_URL not set)");
  }

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
