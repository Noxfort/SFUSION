# SFusion Mapper

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Framework: PySide6](https://img.shields.io/badge/Framework-PySide6%20(Qt6)-green.svg)](https://www.qt.io/)

SFusion Mapper is a powerful open-source Graphical User Interface (GUI) tool designed to act as the "Zero Day" configuration utility for the **SFusion ETL Ecosystem**. Its primary function is to enable users to visually map heterogeneous data sources to specific elements of a network topology, generating a consolidated SQLite database (`.db`) used as the instruction set for the core ETL engine.

## ✨ Key Features

SFusion Mapper provides a visual and isolated environment for data mapping:

* **SUMO Map Import:** Loads complex network topologies in the `.net.xml` and compressed `.net.xml.gz` formats.
* **Heterogeneous Data Sources:** Supports adding and analyzing data from folders containing CSV, JSON, XML, and Excel files.
* **Visual Association:** Allows drag-and-drop or selection-based association of data sources to specific map elements (Nodes/Junctions and Edges/Roads).
* **Local vs. Global Mapping:** Data sources can be defined as **Global** (applied to the entire map) or **Local** (linked to one or more specific elements).
* **Intelligent Edge Handling:** Automatically groups directional road pairs (e.g., "123" and "-123") for consistent naming and association.
* **Project Persistence:** Save and load the entire work state (map data, associations, names) via a dedicated project file (`.sfm.json`).
* **Final Configuration Export:** Generates the final, consolidated SQLite database (`.db`) containing all metadata and mapping instructions.
* **Internationalization (i18n):** User interface supports multiple languages (English, Portuguese, Spanish, French, Russian, Mandarin).

***

## ⚙️ Technical Architecture

The application is built on **Python** and **PySide6 (Qt6)**, adhering strictly to clean code principles:

### Model-View-Controller (MVC) with Builder Pattern

The architecture strictly separates concerns:

* **Builder (`src/core/app_builder.py`):** The single point of entry for application bootstrapping, responsible for creating all components (Views, Models, Controllers, Services) and injecting dependencies.
* **Model (`src/domain/app_state.py`):** The "Single Source of Truth." Stores map data (`MapNode`, `MapEdge`) and associations (`DataSource`) in memory, notifying controllers of changes via Qt Signals.
* **View (`ui/`):** Passive components (e.g., `MainWindow`, `MapView`, `EditorPanel`) that render data and emit user interaction signals.
* **Controller (`src/controllers/`):** Manages application flow and business logic, translating user actions (View signals) into state changes (Model updates).

### Core Layers

| Layer | Key Components | Role |
| :--- | :--- | :--- |
| **Domain/Services** | `MapImporter`, `DataImporter`, `PersistenceService`, `ProjectService` | Handles asynchronous heavy lifting (parsing XML, file analysis, database saving) outside the main thread. |
| **Core/Rendering** | `MapRenderer` | Single responsibility for drawing map elements onto the `QGraphicsScene`, managing colors, and applying visual highlights. |
| **Utilities** | `ConfigManager`, `I18nManager` | Handles external resources like configuration (`settings.json`) and translation files. |

***

## 🚀 Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

* Python 3.9 or higher.
* `pip` and `venv` modules installed.
* **Linux (Ubuntu/Debian):** You may need system libraries for PySide6/Qt:
    ```bash
    sudo apt update
    sudo apt install python3-venv build-essential libqt6gui6 libqt6widgets6 libgl1
    ```

### Local Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/Noxfort-Labs/sfusion-mapper.git](https://github.com/Noxfort-Labs/sfusion-mapper.git)
    cd sfusion-mapper
    ```

2.  **Create and Activate Virtual Environment (venv):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    *(Note: You will see `(venv)` in your terminal prompt.)*

3.  **Install Dependencies:**
    Install all required Python packages from `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Application:**
    Start the GUI application using the Python interpreter inside the virtual environment:
    ```bash
    python sfusion.py
    ```

### Dockerized Setup (GUI in Container)

The project includes configuration to build and run the GUI application inside a Docker container, suitable for environments without direct system dependency installation. This setup requires **X11 forwarding** from your host system (common on Linux).

1.  **Build the Docker Image:**
    ```bash
    docker build -t sfusion-app .
    ```

2.  **Run the Application via Docker Compose (Recommended):**
    The `docker-compose.yml` file is configured to handle the necessary environment variables (`DISPLAY`, `QT_X11_NO_MITSHM`) and volume mounting (`/tmp/.X11-unix`) for the GUI to display on the host.
    ```bash
    docker-compose up
    ```
    *Alternatively, run the image directly:*
    ```bash
    # Ensure DISPLAY is set correctly on your host, e.g., export DISPLAY=:0
    docker run -it --rm \
      -e DISPLAY=$DISPLAY \
      -v /tmp/.X11-unix:/tmp/.X11-unix \
      sfusion-app
    ```

***

## 📦 Building Executable (Linux)

To generate a standalone executable file, the project uses **PyInstaller**. This process is defined in `sfusion.spec`.

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```
2.  **Run the Build Command:**
    ```bash
    pyinstaller sfusion.spec
    ```
    The final executable (`sfusion_mapper`) will be located in the newly created `dist/` folder.

***

## 🤝 Contributing

This project is licensed under the **GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)**.

All contributions are welcome, provided they adhere to the same licensing terms.