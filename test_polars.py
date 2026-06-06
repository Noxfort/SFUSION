import polars as pl
import pandas as pd

df = pl.DataFrame({"flow_val": [None, None, None]})
res = df.select(pl.col("flow_val").cast(pl.Float64).sum())
print("SUM:")
print(res)

res2 = df.select(pl.col("flow_val").cast(pl.Float64).mean())
print("MEAN:")
print(res2)

