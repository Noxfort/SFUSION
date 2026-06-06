import json
import logging
import asyncio
from src.services.neural_transformer import NeuralTransformer
from src.core.schemas import KinematicMap

# Configure logging to see SLM output
logging.basicConfig(level=logging.INFO)

# Run a test for Waze
print("="*50)
print("TESTING WAZE PIPELINE")
print("="*50)

with open('/home/gabriel-moraes/Documentos/output_2/waze/waze_feed_20260608_000000.json') as f:
    waze_events = json.load(f).get("jams", [])

waze_payloads = []
for ev in waze_events:
    waze_payloads.append({
        'sensor_id': 'waze_test',
        'event_timestamp': '2026-06-08T00:00:00Z',
        'data_payload': ev
    })

transformer = NeuralTransformer()
transformer.initialize_encoder()

waze_json_str = json.dumps(waze_events[0] if waze_events else {})
schema = transformer.slm_engine.discover_schema(waze_json_str.encode('utf-8'), "waze")
print(f"SLM SCHEMA FOR WAZE: {schema}")

out_waze = transformer.apply_physics(waze_payloads, schema, assoc_type="LOCAL")
print(f"FINAL OUTPUT FOR WAZE:")
print(out_waze)

