# 📖 Core Concepts

The **SFusion Mapper** is the "Zero Day" graphical interface for the larger **SFusion ETL Ecosystem**. Its primary role is to bridge the gap between raw, unstructured urban sensor data and strict simulation environments (like SUMO).

## 1. Zero-Day Configuration
Unlike traditional ETL pipelines that require hardcoded mappings, SFusion Mapper allows users to visually configure data routing before the pipeline runs. The output is a highly structured SQLite database (`.db`) that serves as a deterministic instruction set for the core headless ETL engine.

## 2. Network Topology & Spatial Association
Traffic data only has value when bound to physical space. SFusion Mapper imports SUMO (`.net.xml`) topologies and represents them as a mathematical graph of **Nodes** (Junctions) and **Edges** (Road segments). 
* **Global Mapping**: Applies data variables across the entire simulation uniformly.
* **Local Mapping**: Associates specific data streams to distinct roads or intersections.

## 3. Neuro-Symbolic Inference
Traditional systems break when a new sensor uses column names like `spd_avg_kmh` instead of `speed`. SFusion utilizes a Small Language Model (SLM) to perform **Schema Discovery**. The SLM acts as an intelligent router, inferring semantic meaning from arbitrary data and mapping it to our strict [[docs/DATA_MODELS|Kinematic Schema]].

For a detailed walkthrough of how these concepts connect in practice, see the [[docs/SYSTEM_WORKFLOW]].

---
*Return to [[docs/INDEX]]*
