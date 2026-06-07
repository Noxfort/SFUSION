# 🖥️ User Guide

This guide walks you through the standard operational procedure for using the SFusion Mapper GUI.

## 1. Importing the Network Topology
* Click **File > Import Map** from the top menu.
* Select your valid SUMO network file (`.net.xml` or compressed `.net.xml.gz`).
* The map will render in the central `MapView`. You can zoom using the scroll wheel and pan by clicking and dragging the canvas.

## 2. Adding Data Sources
* Navigate to the **Data Sources** panel on the left sidebar.
* Click the **Add Source** button and select a directory.
* The system will automatically scan for valid datasets (CSV, JSON, Excel) and populate the list.

## 3. Creating Associations
* **Global Association**: Right-click a data source in the list and select "Set as Global". The neural engine will map its variables to all edges in the simulation simultaneously.
* **Local Association**: Click and drag a data source from the list and drop it onto a specific road segment (Edge) on the map. The edge will highlight in a distinct color, indicating an active local association.

## 4. Validating the Neural Mapping
Once an association is made, the [[docs/NEURAL_PIPELINE|SLM Engine]] will run in the background to deduce schema routing.
* Open the **Editor Panel** on the right sidebar.
* Verify that the inferred `KinematicMap` correctly matches your dataset columns to the required physics variables (Speed, Flow).
* If the SLM made a mistake or hallucinated a column, you can manually override the schema routing using the dropdowns in the Editor Panel.

## 5. Exporting the Configuration
* Once all mapping is complete and validated, click **Export Database**.
* Choose an output directory.
* SFusion will generate the final SQLite `.db` file, which is fully ready to be ingested by the core headless ETL pipeline.

---
*Return to [[docs/INDEX]]*
