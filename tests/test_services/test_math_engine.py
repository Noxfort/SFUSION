import pytest
import polars as pl
from src.services.math_engine import MathEngine
from src.core.schemas import KinematicMap

def test_compile_ast_direct():
    schema = KinematicMap(speed_col="v", flow_col="q", intensity_col="k", confidence_score=1.0)
    exprs = MathEngine.compile_ast(schema)
    assert len(exprs) == 3
    aliases = [e.meta.output_name() for e in exprs]
    assert "speed_val" in aliases
    assert "flow_val" in aliases
    assert "intensity_val" in aliases

def test_compile_ast_derived():
    schema = KinematicMap(distance_col="dist", time_col="t", occupancy_col="occ", confidence_score=1.0)
    exprs = MathEngine.compile_ast(schema)
    assert len(exprs) == 3
    aliases = [e.meta.output_name() for e in exprs]
    assert "speed_val" in aliases
    assert "flow_val" in aliases
    assert "intensity_val" in aliases

def test_compile_aggregations():
    cols = ["speed_val", "flow_val", "intensity_val", "event_timestamp", "sensor_lat", "sensor_lon"]
    agg_exprs = MathEngine.compile_aggregations(cols)
    assert len(agg_exprs) >= 3
    aliases = [e.meta.output_name() for e in agg_exprs]
    assert "speed_val" in aliases
    assert "flow_val" in aliases
    assert "intensity_val" in aliases
    assert "event_timestamp" in aliases
    assert "lat" in aliases
    assert "lon" in aliases

def test_compile_aggregations_minimal():
    cols = ["speed_val"]
    agg_exprs = MathEngine.compile_aggregations(cols)
    assert len(agg_exprs) == 2
    aliases = [e.meta.output_name() for e in agg_exprs]
    assert "speed_val" in aliases
