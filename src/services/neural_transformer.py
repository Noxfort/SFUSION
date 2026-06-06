# SFusion (SYNAPSE Fusion) Mapper
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/services/neural_transformer.py
# Author: Gabriel Moraes
# Date: May 2026
# Description:
#    SOLID Intermediary Layer. Orchestrates the Semantic Encoder (mpnet) 
#    and the Vector Physics Engine (Polars) to normalize heterogeneous data payloads.

import pandas as pd
import numpy as np
import polars as pl
import logging
from typing import List, Optional, Dict

from src.agent.slm_engine import SLMEngine
from src.services.math_engine import MathEngine
from src.core.schemas import KinematicMap

class NeuralTransformer:
    def __init__(self):
        self.slm_engine = None
        self.math_engine = MathEngine()
        self._schema_cache: Dict[str, KinematicMap] = {}

    def initialize_encoder(self):
        """Loads the SLM Engine model (~5GB, instant startup with GPU)."""
        if not self.slm_engine:
            logging.info("NeuralTransformer: Initializing SLMEngine...")
            self.slm_engine = SLMEngine()

    def cleanup_encoder(self):
        """Unloads the SLM Engine from memory."""
        if self.slm_engine:
            logging.info("NeuralTransformer: Unloading SLMEngine...")
            del self.slm_engine
            self.slm_engine = None
        self._schema_cache.clear()

    def discover_schema(self, raw_text: str, folder_name: str) -> Optional[KinematicMap]:
        """
        Uses the Semantic Encoder to classify column names into kinematic properties
        via cosine similarity (tensor dot product). Instantaneous inference.
        """
        # Check cache first — avoid redundant inference for the same sensor type
        if folder_name in self._schema_cache:
            logging.info(f"NeuralTransformer: Schema cache HIT for '{folder_name}'. Skipping inference.")
            return self._schema_cache[folder_name]
        
        logging.info(f"NeuralTransformer: Discovering schema for sensor folder '{folder_name}'...")
        
        global_summary = (
            f"SENSOR FOLDER: {folder_name}\n\n"
            f"RAW FILE CONTENT:\n{raw_text}"
        )
        
        if self.slm_engine:
            schema = self.slm_engine.discover_schema(raw_text, folder_name)
            if schema:
                # Sanity Filter: Wipe out string hallucinations like "NULL"
                for field in ['speed_col', 'flow_col', 'intensity_col', 'distance_col', 'time_col', 'occupancy_col']:
                    val = getattr(schema, field, None)
                    if isinstance(val, str) and val.upper() in ["NULL", "NONE", ""]:
                        setattr(schema, field, None)
                
                # Cache the result for this sensor folder
                self._schema_cache[folder_name] = schema
            return schema
        
        logging.warning("NeuralTransformer: SLMEngine is not initialized.")
        return None

    def apply_physics(self, events: List[dict], schema: Optional[KinematicMap], assoc_type: str = "LOCAL") -> List[dict]:
        """
        Converts the payloads into a Polars vectorized graph, applies the discovered schema 
        to calculate Speed, Flow, and Intensity, and aggregates them.
        """
        if not events:
            return []
            
        payloads = [e.get('data_payload', {}) for e in events]
        df_payload = pd.json_normalize(payloads)
        
        # Inject metadata for grouping and time windowing
        df_payload['event_timestamp'] = [e['event_timestamp'] for e in events]
        df_payload['sensor_id'] = [e['sensor_id'] for e in events]
        
        if schema:
            # Reconcile schema columns with actual DataFrame columns (Extractors strip root keys)
            df_cols = list(df_payload.columns)
            
            def resolve_column(schema_col: Optional[str]) -> Optional[str]:
                if not schema_col: return None
                schema_col_lower = schema_col.lower()
                if schema_col_lower in [c.lower() for c in df_cols]: 
                    return next((c for c in df_cols if c.lower() == schema_col_lower), None)
                
                # Try suffix match (e.g. 'recognitions.vehicle' -> 'vehicle')
                for col in df_cols:
                    if schema_col_lower.endswith('.' + col.lower()) or col.lower().endswith('.' + schema_col_lower):
                        return col
                
                # Try exact basename match
                schema_base = schema_col_lower.split('.')[-1]
                for col in df_cols:
                    if col.lower().split('.')[-1] == schema_base:
                        return col
                        
                # Try substring match in basename as a fallback
                for col in df_cols:
                    col_base = col.lower().split('.')[-1]
                    if schema_base in col_base or col_base in schema_base:
                        return col
                        
                return None

            # Create a localized copy of the schema for this DataFrame to avoid mutating the cache
            local_schema = schema.copy()
            local_schema.speed_col = resolve_column(local_schema.speed_col)
            local_schema.flow_col = resolve_column(local_schema.flow_col)
            local_schema.intensity_col = resolve_column(local_schema.intensity_col)
            local_schema.distance_col = resolve_column(local_schema.distance_col)
            local_schema.time_col = resolve_column(local_schema.time_col)
            local_schema.occupancy_col = resolve_column(local_schema.occupancy_col)
            
            if assoc_type.upper() == "GLOBAL":
                local_schema.flow_col = None
                local_schema.intensity_col = None
            
            pl_df = pl.from_pandas(df_payload)
            exprs = self.math_engine.compile_ast(local_schema)
            pl_df = pl_df.with_columns(exprs)
            
            # --- AGGREGATION (1 Arquivo = 1 Linha) ---
            # Agrupamos apenas pelo sensor_id para que TODOS os eventos lidos dentro deste mesmo arquivo
            # sejam sumariados (Média/Soma) resultando em exatamente 1 linha, não importando quantas
            # coordenadas existam no arquivo.
            group_cols = ["sensor_id"]
            agg_exprs = self.math_engine.compile_aggregations(pl_df.columns)
            pl_df = pl_df.group_by(group_cols).agg(agg_exprs)
            
            df_payload = pl_df.to_pandas()
        else:
            logging.warning("NeuralTransformer: No valid KinematicMap provided. Using null defaults.")
        
        # Guarantee fundamental kinematic variables exist in the payload
        required_cols = ['speed_val', 'flow_val', 'intensity_val', 'lat', 'lon']
        for col in required_cols:
            if col not in df_payload.columns:
                df_payload[col] = None
                
        # Convert pandas numeric formatting appropriately so it serializes natively to JSON
        df_payload['speed_val'] = pd.to_numeric(df_payload['speed_val'], errors='coerce')
        df_payload['flow_val'] = pd.to_numeric(df_payload['flow_val'], errors='coerce')
        df_payload['intensity_val'] = pd.to_numeric(df_payload['intensity_val'], errors='coerce')
        
        # Convert NaN to None for standard JSON compliance
        df_payload = df_payload.replace({np.nan: None})
        
        # Reconstruct events
        enriched_payloads = df_payload.to_dict(orient='records')
        
        aggregated_events = []
        for row in enriched_payloads:
            # Check for failed physics calculations and log explicitly
            missing_kinematics = []
            if row.get('speed_val') is None: missing_kinematics.append('speed_val')
            if row.get('flow_val') is None: missing_kinematics.append('flow_val')
            if row.get('intensity_val') is None: missing_kinematics.append('intensity_val')
            
            sensor_id = row.get('sensor_id', events[0]['sensor_id'])
            
            if missing_kinematics:
                logging.warning(
                    f"NeuralTransformer: [PHYSICS FAILED] Could not calculate {missing_kinematics} "
                    f"for sensor '{sensor_id}'. Missing physical variables or incomplete schema."
                )
            
            # Save ONLY calculated physics + location columns in the payload.
            # Raw data is already preserved compressed in raw_data_storage.
            clean_payload = {
                'speed_val': row.get('speed_val'),
                'flow_val': row.get('flow_val'),
                'intensity_val': row.get('intensity_val'),
                'lat': row.get('lat'),
                'lon': row.get('lon'),
            }
                
            aggregated_events.append({
                'event_timestamp': row.get('event_timestamp', events[0]['event_timestamp']),
                'sensor_id': sensor_id,
                'data_payload': clean_payload
            })
            
        return aggregated_events
