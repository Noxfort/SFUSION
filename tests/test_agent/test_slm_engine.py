import pytest
import json
from unittest.mock import patch, MagicMock
from src.agent.slm_engine import SLMEngine
from src.core.schemas import KinematicMap

def test_slm_engine_init_no_llama():
    with patch('src.agent.slm_engine.Llama', None):
        engine = SLMEngine()
        assert engine.llm is None

def test_slm_engine_init_success():
    mock_llama = MagicMock()
    with patch('src.agent.slm_engine.Llama', mock_llama):
        engine = SLMEngine(model_path="dummy.gguf")
        assert engine.llm is not None

def test_build_prompt():
    engine = SLMEngine()
    raw_content = '{"col1": 1, "col2": 2}'
    prompt = engine._build_prompt(raw_content, "TestSource", "GLOBAL")
    assert prompt is not None
    assert "Available Columns in Dataset:" in prompt

def test_discover_schema():
    mock_llama = MagicMock()
    # Mock LLM response
    mock_llama.return_value = {
        "choices": [{"text": "<think>Thinking</think>\n{\"speed_col\": \"col1\"}"}]
    }
    
    with patch('src.agent.slm_engine.Llama', mock_llama):
        engine = SLMEngine(model_path="dummy.gguf")
        engine.llm = mock_llama
        
        result = engine.discover_schema('{"col1": 1}', "Test", "GLOBAL")
        assert isinstance(result, KinematicMap)
        assert result.speed_col == "col1"
        
def test_unload():
    mock_llama = MagicMock()
    with patch('src.agent.slm_engine.Llama', mock_llama):
        engine = SLMEngine(model_path="dummy.gguf")
        engine.llm = mock_llama
        engine.unload()
        assert engine.llm is None
