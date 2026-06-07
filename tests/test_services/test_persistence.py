import pytest
import sqlite3
import os
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication
from src.services.persistence import PersistenceWorker, PersistenceService
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

def test_persistence_worker_create_db(tmp_path, app_state):
    db_path = str(tmp_path / "test.db")
    
    node = MapNode(id="n1", x=0, y=0, real_name="Node 1")
    edge = MapEdge(id="e1", from_node="n1", to_node="n2", real_name="Edge 1")
    ds = DataSource(path="/fake", name="Source 1", association_type=AssociationType.GLOBAL)
    
    app_state.set_map_data([node], [edge])
    app_state.add_data_source(ds)
    
    worker = PersistenceWorker(db_path, app_state)
    worker.run()
    
    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT sumo_id, real_name FROM node_metadata")
    assert cursor.fetchone() == ("n1", "Node 1")
    
    cursor.execute("SELECT sumo_id, real_name FROM edge_metadata")
    assert cursor.fetchone() == ("e1", "Edge 1")
    
    cursor.execute("SELECT source_name FROM data_associations")
    assert cursor.fetchone()[0] == "Source 1"
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='section_source_1'")
    assert cursor.fetchone() is not None
    conn.close()

def test_persistence_service(app_state):
    service = PersistenceService(app_state)
    with patch.object(service._thread_pool, 'start') as mock_start:
        service.save_configuration('/fake/path')
        mock_start.assert_called_once()
