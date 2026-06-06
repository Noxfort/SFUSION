import json
from src.services.neural_transformer import NeuralTransformer
from src.core.schemas import KinematicMap

with open('/home/gabriel-moraes/Documentos/output_2/waze/waze_feed_20260608_000000.json') as f:
    events = json.load(f)

if isinstance(events, dict):
    # Depending on Waze JSON structure, events might be under a key
    if 'jams' in events:
        events = events['jams']
    else:
        events = [events]

wrapped_events = []
for ev in events:
    wrapped_events.append({
        'sensor_id': 'waze_1',
        'event_timestamp': '2026-06-08T00:00:00Z',
        'data_payload': ev
    })

schema = KinematicMap(speed_col='speed_kmh', flow_col=None, intensity_col='level')

transformer = NeuralTransformer()
out = transformer.apply_physics(wrapped_events, schema, assoc_type="LOCAL")
import pprint
pprint.pprint(out)

