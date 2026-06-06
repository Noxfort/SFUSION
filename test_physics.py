import polars as pl
import pandas as pd
from src.core.schemas import KinematicMap
from src.services.math_engine import MathEngine

df = pd.DataFrame({
    'sensor_id': ['cam_1'],
    'event_timestamp': ['2026-06-08T00:00:00Z'],
    'estimated_speed_kmh': [60.5]
})
print("Initial df:")
print(df)

schema = KinematicMap(speed_col='estimated_speed_kmh')

pl_df = pl.from_pandas(df)
engine = MathEngine()
exprs = engine.compile_ast(schema)
pl_df = pl_df.with_columns(exprs)

print("After AST:")
print(pl_df)

agg_exprs = engine.compile_aggregations(pl_df.columns)
pl_df = pl_df.group_by(['sensor_id']).agg(agg_exprs)

print("After Aggregation:")
print(pl_df)

df_payload = pl_df.to_pandas()
print("Final Dicts:")
print(df_payload.to_dict(orient='records'))

