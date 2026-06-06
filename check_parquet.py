import pandas as pd
df = pd.read_parquet('/home/gabriel-moraes/Documentos/DADOS/a.parquet')
print(df[['sensor_id', 'speed_val', 'flow_val', 'intensity_val', 'source_table']].head(24))
