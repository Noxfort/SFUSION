import pytest
from src.core.schemas import KinematicMap

def test_kinematic_map_empty():
    kmap = KinematicMap()
    assert kmap.speed_col is None
    assert kmap.flow_col is None
    assert kmap.intensity_col is None
    assert kmap.distance_col is None
    assert kmap.time_col is None
    assert kmap.occupancy_col is None
    assert kmap.confidence_score is None

def test_kinematic_map_with_data():
    kmap = KinematicMap(
        speed_col="velocidade",
        flow_col="fluxo",
        confidence_score=0.95
    )
    assert kmap.speed_col == "velocidade"
    assert kmap.flow_col == "fluxo"
    assert kmap.confidence_score == 0.95
    assert kmap.intensity_col is None
