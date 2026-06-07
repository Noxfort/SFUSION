# 🧠 Neural Pipeline & SLM Engine

SFusion relies on a Small Language Model (SLM) — currently *Phi-4-mini* — to perform intelligent semantic routing. This is handled by the `SLMEngine` module.

## Neuro-Symbolic Architecture

The system uses a **neuro-symbolic** approach:
* **Neural**: The SLM reads the raw data (JSON/CSV) and "understands" the context, acting dynamically to infer spatial and temporal metadata.
* **Symbolic**: The output is strictly constrained to a predefined JSON schema (`KinematicMap`), guaranteeing type safety for the deterministic physics engine.

## The SLM Engine

### 1. Hardware Acceleration
The engine utilizes `llama.cpp` and hardware acceleration (TensorCores via FlashAttention) for low-latency inference. 
* **KV Cache Control**: Inference is kept strictly isolated per-batch to prevent VRAM memory leaks, dropping context between disparate datasets.
* **Telemetry**: System metrics are tracked dynamically via `nvidia-smi` and `psutil` to ensure resource stability (see `[[src/utils/slm_telemetry.py]]`).

### 2. Prompt Engineering & Ingestion
The `SLMEngine` extracts available dataset columns programmatically and injects them into the context window. It prevents hallucinations by forcing the model to select *only* from the provided variables.

### 3. Output Parsing
The system explicitly separates the SLM's "thinking/reasoning" block from its structured JSON output. This ensures that only pure data maps are serialized to the `KinematicMap` domain model, preventing parsing errors during high-volume ETL ingestion.

## Related Source Files
* `[[src/agent/slm_engine.py]]` - Core SLM integration and LLM context management.
* `[[src/utils/slm_telemetry.py]]` - Resource logging and GPU VRAM monitoring.
* `[[src/core/schemas.py]]` - Pydantic validation schemas.

---
*Return to [[docs/INDEX]]*
