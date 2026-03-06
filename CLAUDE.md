# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP-server with RAG for 1C metadata. The system allows AI agents (Cursor, VS Code Copilot, RooCode) to query the structure of a specific 1C configuration to generate accurate code and queries instead of hallucinating object names.

**Target users:** 1C analysts and developers working with rare/industry-specific configurations whose structure is unknown to standard LLMs.

Supports any 1C:Enterprise 8.3 configuration exported to XML. Tested with configurations containing ~6000 metadata objects.

## Project Status

**All stages complete.** Full pipeline working: XML Parser → Embedding Service → Qdrant → MCP Server. All 5 Docker services operational.

## Commands

```bash
# Run tests
cd parser && python3 -m pytest tests/test_parser.py -v

# Export parsed metadata to JSON
cd parser && python3 export.py "../Конфигуратор/Prod" "../parsed_metadata"

# Start Docker (parser + qdrant)
docker compose up qdrant parser --build -d

# Check parser API
curl http://localhost:8001/health
curl http://localhost:8001/stats
curl http://localhost:8001/parse/Catalog/Номенклатура
```

## Architecture

4 microservices in Docker: parser (Python/FastAPI :8001), embeddings (Python/FastAPI/BERTA :5000), loader (Python/Streamlit :8501), mcp-server (TypeScript/MCP SDK :8000).

Vector DB: Qdrant (:6333). Hybrid search: dense (BERTA 768d) + sparse (BM25) + RRF fusion.

## Parser Details

36 object types parsed from `Конфигуратор/Prod/`:
- Core data: Catalog, Document, AccumulationRegister, InformationRegister, AccountingRegister, Enum, Constant
- References: ChartOfAccounts, ChartOfCharacteristicTypes, ExchangePlan, BusinessProcess, Task
- Metadata: DefinedType, DocumentJournal, DataProcessor, Report
- Code: CommonModule (with server/client/privileged flags)
- Structure: Subsystem (recursive), EventSubscription, ScheduledJob
- Services: HTTPService (URL templates), WebService (operations), CommonCommand
- Config: FunctionalOption, CommonAttribute, Role, XDTOPackage
- Additional: SessionParameter, CommonForm, ExternalDataSource, FilterCriterion, Sequence, FunctionalOptionsParameter, DocumentNumerator, CommandGroup, SettingsStorage

Extra data extracted:
- `.bsl` module code (ObjectModule, ManagerModule, Module, etc.) — 3032 files
- Predefined elements from `Ext/Predefined.xml` — 2669 items
- Nested subsystems (recursive) — 248 total (49 top-level)

## Key Files

- `docs/implementation-plan.md` — full plan with 23 tasks (6 stages)
- `parser/xml_parser.py` — core XML parsing logic
- `parser/models.py` — Pydantic models (36 ObjectTypes)
- `parser/export.py` — export to JSON + .bsl files
- `parsed_metadata/` — exported data (all_metadata.json 16MB without code, modules/ 160MB .bsl)

## 1C XML Structure

XML namespace: `http://v8.1c.ru/8.3/MDClasses`. Each `.xml` file wraps a `<MetaDataObject>` with child element named after the type (e.g., `<Catalog>`, `<Document>`). Properties in `<md:Properties>`, child objects in `<md:ChildObjects>`.

## Language

All documentation and user-facing text in Russian. 1C uses Russian-language identifiers.
