import pytest
from src.services.extractors import UniversalExtractor
from datetime import datetime

def test_extract_json():
    ext = UniversalExtractor()
    content = b'[{"speed": 50, "time": 1600000000000}]'
    res = ext.extract("test.json", content, "sensor1")
    assert len(res) == 1
    assert res[0]["sensor_id"] == "sensor1"
    assert "event_timestamp" in res[0]
    assert res[0]["data_payload"]["speed"] == 50

def test_extract_json_dict():
    ext = UniversalExtractor()
    content = b'{"alerts": [{"speed": 50}]}'
    res = ext.extract("test.json", content, "sensor1")
    assert len(res) == 1
    assert res[0]["data_payload"]["speed"] == 50

def test_extract_csv():
    ext = UniversalExtractor()
    content = b'speed,time\n50,160000'
    res = ext.extract("test.csv", content, "sensor2")
    assert len(res) == 1
    assert res[0]["data_payload"]["speed"] == "50"
    
def test_extract_invalid():
    ext = UniversalExtractor()
    # CSV reader might still process it as a single empty column row, so we just ensure it doesn't crash
    content = b'\x00\x01\x02'
    res = ext.extract("test.bin", content)
    assert isinstance(res, list)
