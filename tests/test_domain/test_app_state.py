import pytest
from PySide6.QtCore import QCoreApplication
from src.domain.app_state import AppState
from src.domain.entities import MapNode, MapEdge, DataSource, AssociationType

@pytest.fixture(scope="session")
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    yield app

@pytest.fixture
def app_state(qapp):
    return AppState()

def test_initial_state(app_state):
    assert len(app_state.get_all_nodes()) == 0
    assert len(app_state.get_all_edges()) == 0
    assert len(app_state.get_all_data_sources()) == 0
    assert not app_state.is_in_association_mode()

def test_set_map_data(app_state):
    nodes = [MapNode(id="n1", x=0, y=0)]
    edges = [MapEdge(id="e1", from_node="n1", to_node="n2")]
    
    app_state.set_map_data(nodes, edges)
    
    assert len(app_state.get_all_nodes()) == 1
    assert len(app_state.get_all_edges()) == 1
    assert app_state.get_node_by_id("n1") == nodes[0]
    assert app_state.get_edge_by_id("e1") == edges[0]

def test_add_data_source(app_state):
    ds = DataSource(path="/tmp/d1", name="Data 1")
    app_state.add_data_source(ds)
    
    assert len(app_state.get_all_data_sources()) == 1
    assert app_state.get_data_source_by_id("/tmp/d1") == ds

def test_delete_data_source(app_state):
    ds = DataSource(path="/tmp/d1", name="Data 1")
    app_state.add_data_source(ds)
    app_state.delete_data_source("/tmp/d1")
    
    assert len(app_state.get_all_data_sources()) == 0

def test_association_mode(app_state):
    ds = DataSource(path="/tmp/d1", name="Data 1")
    app_state.add_data_source(ds)
    app_state.set_selected_data_source("/tmp/d1")
    
    app_state.enter_association_mode()
    assert app_state.is_in_association_mode()
    
    app_state.exit_association_mode()
    assert not app_state.is_in_association_mode()

def test_associate_source_to_element(app_state):
    ds = DataSource(path="/tmp/d1", name="Data 1")
    nodes = [MapNode(id="n1", x=0, y=0)]
    app_state.set_map_data(nodes, [])
    app_state.add_data_source(ds)
    app_state.set_selected_data_source("/tmp/d1")
    
    app_state.associate_selected_source_to_element("n1")
    
    source = app_state.get_data_source_by_id("/tmp/d1")
    assert source.associated_element_id == "n1"
    assert source.association_type == AssociationType.LOCAL
