import json
import logging
from src.services.neural_transformer import NeuralTransformer
from src.core.schemas import KinematicMap
import pandas as pd
import numpy as np

with open('/home/gabriel-moraes/Documentos/output_2/Tomtom/tomtom_flow_20260608_000000.json') as f:
    events = json.load(f)

if isinstance(events, dict):
    events = [events]

# Wrap in standard format
wrapped_events = []
for ev in events:
    wrapped_events.append({
        'sensor_id': 'tomtom_1',
        'event_timestamp': '2026-06-08T00:00:00Z',
        'data_payload': ev
    })

schema = KinematicMap(speed_col='currentSpeed_kmh', flow_col=None, intensity_col=None)

transformer = NeuralTransformer()
out = transformer.apply_physics(wrapped_events, schema, assoc_type="LOCAL")
print("TRANSFORMER OUTPUT:")
import pprint
pprint.pprint(out)

