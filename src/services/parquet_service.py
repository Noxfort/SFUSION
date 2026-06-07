# SFusion (SYNAPSE Fusion) Mapper
#
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/services/parquet_service.py
# Author: Gabriel Moraes
# Date: May 2026
# Description:
#    ParquetService (Service). The fast Medallion Exporter.
#    Since Physics and SLM are applied during Ingestion (ETLService), 
#    this service merely unwraps the Gold SQLite DB and exports it to Parquet.

import sqlite3
import pandas as pd
import json
import logging
import os
from PySide6.QtCore import QObject, Slot, QRunnable, QThreadPool, Signal

class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(str)

class ParquetExportWorker(QRunnable):
    def __init__(self, db_path: str, output_path: str = None):
        super().__init__()
        self.db_path = db_path
        self.output_path = output_path 
        self.sensor_map = {} 
        self.signals = WorkerSignals()

    def _load_sensor_mapping(self, conn: sqlite3.Connection):
        try:
            query = """
                SELECT da.source_name, da.association_type, da.associated_element_id, em.real_name 
                FROM data_associations da
                LEFT JOIN edge_metadata em ON da.associated_element_id = em.sumo_id
            """
            cursor = conn.cursor()
            cursor.execute(query)
            for row in cursor.fetchall():
                source_name, assoc_type, sumo_id, street_name = row
                self.sensor_map[source_name.lower()] = {
                    "sumo_id": sumo_id,
                    "location_text": street_name,
                    "association_type": assoc_type
                }
        except Exception as e:
            logging.warning(f"ParquetExport: Could not load sensor mapping: {e}")

    def _process_table(self, table_name: str, conn: sqlite3.Connection) -> pd.DataFrame:
        try:
            logging.info(f"ParquetExport: Unpacking '{table_name}'...")
            query = f"SELECT event_timestamp, sensor_id, data_payload FROM {table_name}"
            df = pd.read_sql_query(query, conn)
            
            if df.empty: return pd.DataFrame()

            def safe_unpack(x):
                try: return json.loads(x)
                except: return {}
                
            payloads = df['data_payload'].apply(safe_unpack).tolist()
            df_payload = pd.json_normalize(payloads)
            
            # Prevent "duplicate keys" error by stripping out reserved columns from the raw payload
            reserved_cols = ['event_timestamp', 'sensor_id', 'id']
            for rc in reserved_cols:
                if rc in df_payload.columns:
                    df_payload.drop(columns=[rc], inplace=True)
            
            # The payload already contains the calculated physics from NeuralTransformer!
            df = pd.concat([df[['event_timestamp', 'sensor_id']], df_payload], axis=1)
            
            # Ensure columns exist in case some rows are totally empty
            required_cols = ['speed_val', 'flow_val', 'intensity_val', 'lat', 'lon']
            for col in required_cols:
                if col not in df.columns: df[col] = None

            df['source_table'] = table_name
            df['event_timestamp'] = pd.to_datetime(df['event_timestamp'], utc=True, format='mixed', errors='coerce')
            
            import numpy as np
            # Replace infinities with np.nan first so we can safely round them
            df['speed_val'] = pd.to_numeric(df['speed_val'], errors='coerce').replace([np.inf, -np.inf], np.nan)
            df['speed_val'] = df['speed_val'].round(0).astype('Int64')
            
            df['flow_val'] = pd.to_numeric(df['flow_val'], errors='coerce').replace([np.inf, -np.inf], np.nan).round(2)
            df['intensity_val'] = pd.to_numeric(df['intensity_val'], errors='coerce').replace([np.inf, -np.inf], np.nan).round(2)
            
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            
            # --- LOCATION MAPPING ---
            def get_assoc_type(sid):
                return self.sensor_map.get(str(sid).lower(), {}).get('association_type', 'LOCAL')
            
            df['origin_type'] = df['sensor_id'].apply(get_assoc_type)
            
            def get_sumo_id(row):
                if row['origin_type'] == "GLOBAL": return None
                return self.sensor_map.get(str(row['sensor_id']).lower(), {}).get('sumo_id')
                
            def get_location(row):
                if row['origin_type'] == "GLOBAL": return None
                key = str(row['sensor_id']).lower()
                mapped = self.sensor_map.get(key, {}).get('location_text')
                return mapped if mapped else row.get('location_text_raw')

            df['sumo_id'] = df.apply(get_sumo_id, axis=1)
            df['location_text'] = df.apply(get_location, axis=1)
            
            if 'location_text_raw' in df.columns:
                df.drop(columns=['location_text_raw'], inplace=True)

            final_cols = [
                'event_timestamp', 'sensor_id', 'sumo_id', 'location_text',
                'lat', 'lon', 'origin_type', 'speed_val', 'flow_val', 
                'intensity_val', 'source_table'
            ]
            for col in final_cols:
                if col not in df.columns:
                    df[col] = None
            return df[final_cols]

        except Exception as e:
            logging.error(f"ParquetExport: Error in {table_name}: {e}")
            return pd.DataFrame()

    @Slot()
    def run(self):
        logging.info(f"ParquetExport: Executing clean Medallion export for '{self.db_path}'...")
        
        if not os.path.exists(self.db_path):
            self.signals.error.emit("DB file not found")
            return

        if self.output_path:
            final_path = self.output_path
        else:
            output_dir = os.path.dirname(self.db_path)
            output_filename = f"{os.path.splitext(os.path.basename(self.db_path))[0]}_unified.parquet"
            final_path = os.path.join(output_dir, output_filename)
        
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            self._load_sensor_mapping(conn)
            
            # Dynamically find all specialized section tables
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'section_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            dfs = []
            for tbl in tables:
                dfs.append(self._process_table(tbl, conn))
            
            valid_dfs = [d for d in dfs if not d.empty]
            
            if valid_dfs:
                logging.info("ParquetExport: Merging datasets...")
                full_df = pd.concat(valid_dfs, ignore_index=True)
                full_df.sort_values(by='event_timestamp', inplace=True)
                
                full_df.to_parquet(final_path, index=False, compression='snappy')
                
                logging.info(f"ParquetExport: SUCCESS. Saved unified dataset: {final_path}")
            else:
                logging.warning("ParquetExport: No data found in any section.")

            self.signals.finished.emit()

        except Exception as e:
            logging.error(f"ParquetExport: Critical Error: {e}", exc_info=True)
            self.signals.error.emit(str(e))
        finally:
            if conn: conn.close()


class ParquetService(QObject):
    export_finished = Signal()

    def __init__(self):
        super().__init__()
        self._thread_pool = QThreadPool.globalInstance()
        logging.info("ParquetService (Service) initialized.")

    @Slot(str, str)
    def export_db_to_parquet(self, db_path: str, output_path: str = None):
        worker = ParquetExportWorker(db_path, output_path)
        worker.signals.finished.connect(self.export_finished)
        self._thread_pool.start(worker)