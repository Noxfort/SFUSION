import sqlite3
import pandas as pd
from src.services.parquet_service import ParquetService

df = pd.read_parquet('/home/gabriel-moraes/Documentos/DADOS/a.parquet')
print("--- Parquet Output ---")
print(df[['sensor_id', 'speed_val', 'flow_val', 'intensity_val']].head(24))
