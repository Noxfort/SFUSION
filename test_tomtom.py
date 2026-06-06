import json
import pandas as pd
with open('/home/gabriel-moraes/Documentos/output_2/Tomtom/tomtom_flow_20260608_000000.json') as f:
    events = json.load(f)
if isinstance(events, dict):
    events = [events]

df = pd.json_normalize(events)
print("COLUMNS IN TOMTOM DF:")
print(list(df.columns))
