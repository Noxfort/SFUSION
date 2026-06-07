import pytest
from unittest.mock import patch, mock_open, MagicMock
from PySide6.QtCore import QCoreApplication
from src.services.map_importer import MapImportWorker, NetXMLParserTarget, MapImporter
from src.domain.app_state import AppState

@pytest.fixture(scope="session")
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    yield app

@pytest.fixture
def app_state(qapp):
    return AppState()

def test_net_xml_parser_target():
    target = NetXMLParserTarget()
    
    target.start("junction", {"id": "n1", "x": "10.5", "y": "20.5"})
    assert len(target.nodes) == 1
    assert target.nodes[0].id == "n1"
    
    target.start("edge", {"id": "e1", "from": "n1", "to": "n2"})
    target.start("lane", {"shape": "10.5,20.5 30.0,40.0"})
    target.end("edge")
    
    assert len(target.edges) == 1
    assert target.edges[0].id == "e1"
    assert len(target.edges[0].shape) == 2
    assert target.edges[0].shape[0] == (10.5, 20.5)

def test_map_import_worker_run(app_state):
    worker = MapImportWorker('/fake/map.net.xml', app_state)
    mock_nodes = [MagicMock()]
    mock_edges = [MagicMock()]
    
    with patch.object(worker, '_parse_net_xml', return_value=(mock_nodes, mock_edges)):
        worker.run()
        assert len(app_state.get_all_nodes()) == 1

def test_map_importer_load_map(app_state):
    importer = MapImporter(app_state)
    with patch.object(importer._thread_pool, 'start') as mock_start:
        importer.load_map('/fake/map.net.xml')
        mock_start.assert_called_once()
        
    with patch.object(importer._thread_pool, 'start') as mock_start:
        importer.load_map('')
        mock_start.assert_not_called()
