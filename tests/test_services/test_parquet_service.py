import pytest
import sqlite3
import pandas as pd
from unittest.mock import patch, MagicMock
from PySide6.QtCore import QCoreApplication
from src.services.parquet_service import ParquetExportWorker, ParquetService

@pytest.fixture(scope="session")
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    yield app

def test_load_sensor_mapping():
    worker = ParquetExportWorker("dummy.db")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("Sensor1", "LOCAL", "edge_1", "Main St")]
    mock_conn.cursor.return_value = mock_cursor
    
    worker._load_sensor_mapping(mock_conn)
    assert "sensor1" in worker.sensor_map
    assert worker.sensor_map["sensor1"]["sumo_id"] == "edge_1"

@patch('src.services.parquet_service.pd.read_sql_query')
def test_process_table(mock_read_sql):
    worker = ParquetExportWorker("dummy.db")
    
    df = pd.DataFrame({
        "event_timestamp": ["2026-01-01T00:00:00Z"],
        "sensor_id": ["sensor1"],
        "data_payload": ['{"speed_val": 50, "lat": -23.5}']
    })
    mock_read_sql.return_value = df
    
    mock_conn = MagicMock()
    res = worker._process_table("section_test", mock_conn)
    assert not res.empty
    assert res.iloc[0]["speed_val"] == 50
    assert "lat" in res.columns
    assert "lon" in res.columns

@patch('os.path.exists', return_value=False)
def test_worker_run_db_not_found(mock_exists):
    worker = ParquetExportWorker("missing.db")
    worker.run()
    
def test_parquet_service():
    service = ParquetService()
    with patch.object(service._thread_pool, 'start') as mock_start:
        service.export_db_to_parquet("test.db")
        mock_start.assert_called_once()
