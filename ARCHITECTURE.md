# ⚙️ Technical Architecture

This document outlines the core architecture of the **SFusion Mapper** project.

## Overview

The application is built on **Python** and **PySide6 (Qt6)**, adhering strictly to clean code principles and the Model-View-Controller (MVC) pattern.

See also: [[README]] for general project information.

## Model-View-Controller (MVC) with Builder Pattern

The architecture strictly separates concerns:

* **Builder (`src/core/app_builder.py`):** The single point of entry for application bootstrapping, responsible for creating all components (Views, Models, Controllers, Services) and injecting dependencies.
* **Model (`src/domain/app_state.py`):** The "Single Source of Truth." Stores map data (`MapNode`, `MapEdge`) and associations (`DataSource`) in memory, notifying controllers of changes via Qt Signals.
* **View (`ui/`):** Passive components (e.g., `MainWindow`, `MapView`, `EditorPanel`) that render data and emit user interaction signals.
* **Controller (`src/controllers/`):** Manages application flow and business logic, translating user actions (View signals) into state changes (Model updates).

## Core Layers

| Layer | Key Components | Role |
| :--- | :--- | :--- |
| **Domain/Services** | `MapImporter`, `DataImporter`, `PersistenceService`, `ProjectService` | Handles asynchronous heavy lifting (parsing XML, file analysis, database saving) outside the main thread. |
| **Core/Rendering** | `MapRenderer` | Single responsibility for drawing map elements onto the `QGraphicsScene`, managing colors, and applying visual highlights. |
| **Utilities** | `ConfigManager`, `I18nManager` | Handles external resources like configuration (`settings.json`) and translation files. |

## Neural & SLM Components

The system implements advanced neural schema discovery using a localized Small Language Model (SLM) backend:
* **SLMEngine**: `[[src/agent/slm_engine.py]]`
* **SLM Telemetry**: `[[src/utils/slm_telemetry.py]]`

---
*Return to [[docs/INDEX]] or [[README]]*
