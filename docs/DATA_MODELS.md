# 🗃️ Data Models & State

SFusion utilizes a strict domain-driven design. The application state acts as the Single Source of Truth (SSOT), decoupling the UI from the heavy data lifting.

## Application State (`src/domain/app_state.py`)

The memory model is highly reactive. It holds:
* **Map Elements**: Instances of `MapNode` and `MapEdge`. Edges are automatically grouped if they represent opposite directions of the same road (e.g. `123` and `-123`).
* **Data Sources**: Instances of `DataSource` representing physical files and their metadata.
* **Associations**: The relationships binding `DataSource` to `MapEdge`.

## Kinematic Schema (`src/core/schemas.py`)

The `KinematicMap` is the most critical schema within the ecosystem. It defines the universal parameters required for urban simulation:

```python
class KinematicMap(BaseModel):
    speed_col: Optional[str]
    flow_col: Optional[str]
    intensity_col: Optional[str]
    distance_col: Optional[str]
    time_col: Optional[str]
    occupancy_col: Optional[str]
    confidence_score: float
```

The [[docs/NEURAL_PIPELINE|SLM Engine]] is solely responsible for populating this schema by mapping real-world column names (e.g., `velocidade_media`) to standard fields (`speed_col`).

## Project Persistence (`.sfm.json`)

The entire domain state can be serialized to a `.sfm.json` file via the `ProjectService`. This allows users to save their visual mapping progress without compiling the final ETL database, enabling long-term configuration of complex smart-city topologies.

---
*Return to [[docs/INDEX]]*
