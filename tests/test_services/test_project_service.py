import pytest
import os
import json
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication
from src.services.project_service import ProjectSaveWorker, ProjectLoadWorker, ProjectService
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
    state = AppState()
    return state

def test_project_save_worker(tmp_path, app_state):
    file_path = str(tmp_path / "test.sfm.json")
    
    node = MapNode(id="n1", x=0, y=0)
    app_state.set_map_data([node], [])
    
    worker = ProjectSaveWorker(file_path, app_state)
    worker.run()
    
    assert os.path.exists(file_path)
    with open(file_path, 'r') as f:
        data = json.load(f)
        assert "nodes" in data
        assert len(data["nodes"]) == 1

def test_project_load_worker(tmp_path, app_state):
    file_path = str(tmp_path / "load.sfm.json")
    data = {
        "nodes": [{"id": "n1", "x": 0, "y": 0, "node_type": "unknown", "real_name": None}],
        "edges": [],
        "data_sources": [
            {"path": "/d1", "name": "d1", "file_types": [], "id": "id1", "parser_id": None, "association_type": "GLOBAL", "associated_element_id": None}
        ]
    }
    with open(file_path, 'w') as f:
        json.dump(data, f)
        
    worker = ProjectLoadWorker(file_path, app_state)
    worker.run()
    
    assert len(app_state.get_all_nodes()) == 1
    assert len(app_state.get_all_data_sources()) == 1
    assert app_state.get_all_data_sources()[0].association_type == AssociationType.GLOBAL

def test_project_service(app_state):
    service = ProjectService(app_state)
    with patch.object(service._thread_pool, 'start') as mock_start:
        service.save_project('/fake.json')
        mock_start.assert_called_once()
        
    with patch.object(service._thread_pool, 'start') as mock_start:
        service.load_project('/fake.json')
        mock_start.assert_called_once()
