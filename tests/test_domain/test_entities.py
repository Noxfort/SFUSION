import pytest
from src.domain.entities import DataSource, AssociationType, MapNode, MapEdge

def test_datasource_default_initialization():
    ds = DataSource(path="/tmp/data.csv", name="Data")
    assert ds.path == "/tmp/data.csv"
    assert ds.name == "Data"
    assert ds.file_types == []
    assert ds.id.startswith("src_")
    assert ds.parser_id is None
    assert ds.association_type == AssociationType.UNASSOCIATED
    assert ds.associated_element_id is None

def test_datasource_custom_initialization():
    ds = DataSource(
        path="/tmp/test.json",
        name="Test Source",
        file_types=["JSON"],
        parser_id="json_parser",
        association_type=AssociationType.GLOBAL
    )
    assert ds.file_types == ["JSON"]
    assert ds.parser_id == "json_parser"
    assert ds.association_type == AssociationType.GLOBAL

def test_mapnode_initialization():
    node = MapNode(id="node_1", x=10.5, y=20.5)
    assert node.id == "node_1"
    assert node.x == 10.5
    assert node.y == 20.5
    assert node.node_type == "unknown"
    assert node.real_name is None

def test_mapedge_initialization():
    edge = MapEdge(id="edge_1", from_node="node_1", to_node="node_2")
    assert edge.id == "edge_1"
    assert edge.from_node == "node_1"
    assert edge.to_node == "node_2"
    assert edge.shape == []
    assert edge.real_name is None
