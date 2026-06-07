# 🔄 System Workflow

The SFusion Mapper follows a deterministic, 4-phase lifecycle to convert raw user input into an actionable ETL database.

## Phase 1: Map Topology Ingestion
1. The user imports a network map (`.net.xml` or `.net.xml.gz`).
2. The `MapImporter` service asynchronously parses the XML, constructing spatial representations (`MapNode`, `MapEdge`).
3. The `MapRenderer` draws the graph onto the PySide6 `QGraphicsScene`.

## Phase 2: Data Source Registration
1. The user selects a directory containing raw datasets (CSV, JSON, XML, Excel).
2. The `DataImporter` recursively analyzes the files and parses headers.
3. The system registers these as isolated `DataSource` entities within the [[ARCHITECTURE|Model]].

## Phase 3: Association & Schema Discovery
This is the core value proposition of SFusion.
1. The user associates a `DataSource` with a `MapEdge` (Local) or the entire graph (Global).
2. The system triggers the **SLMEngine** (see [[docs/NEURAL_PIPELINE]]).
3. The SLM infers the mapping between the raw data columns and the required `KinematicMap` variables (Speed, Flow, Intensity).

## Phase 4: Compilation & Export
1. The user triggers the export process.
2. The `PersistenceService` aggregates the topology, the data sources, and the inferred neural mappings.
3. A consolidated SQLite `.db` is generated, which is subsequently consumed by the headless ETL execution engine to run the traffic simulation.

---
*Return to [[docs/INDEX]]*
