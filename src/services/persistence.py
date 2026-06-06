# SFusion (SYNAPSE Fusion) Mapper - "Day Zero" ETL Configuration Tool
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/services/persistence.py
# Author: Gabriel Moraes
# Date: November 2025

import logging
import sqlite3
import json
from PySide6.QtCore import QObject, Slot, QRunnable, QThreadPool

from src.domain.app_state import AppState


class PersistenceWorker(QRunnable):
    """
    Worker to save the configuration to a .db in a separate thread.
    Also ensures the raw data table schema and specialized sections exist.
    """
    def __init__(self, file_path: str, app_state: AppState):
        super().__init__()
        self.file_path = file_path
        self._app_state = app_state 

    @Slot()
    def run(self):
        """Executes the saving logic."""
        logging.info(f"PersistenceWorker: Starting save to '{self.file_path}'...")
        try:
            nodes = self._app_state.get_all_nodes()
            edges = self._app_state.get_all_edges()
            sources = self._app_state.get_all_data_sources()
            
            self._create_database_and_save(nodes, edges, sources)
            logging.info(f"PersistenceWorker: Configuration successfully saved to {self.file_path}")

        except sqlite3.Error as e:
            logging.error(f"PersistenceWorker: SQLite error while saving to {self.file_path}: {e}")
        except Exception as e:
            logging.error(f"PersistenceWorker: Unexpected failure while saving configuration: {e}", exc_info=True)

    def _create_database_and_save(self, nodes, edges, sources):
        """
        Creates/Replaces the metadata tables and inserts the configuration data.
        Ensures the raw_data_storage and specialized section tables exist.
        """
        with sqlite3.connect(self.file_path) as conn:
            cursor = conn.cursor()
            
            # --- Table 1: Node Metadata (Nodes/Junctions) ---
            cursor.execute("DROP TABLE IF EXISTS node_metadata")
            cursor.execute("""
                CREATE TABLE node_metadata (
                    sumo_id TEXT PRIMARY KEY,
                    real_name TEXT
                )
            """)
            node_data = [
                (n.id, n.real_name) for n in nodes if n.real_name
            ]
            if node_data:
                cursor.executemany("INSERT INTO node_metadata VALUES (?, ?)", node_data)

            # --- Table 2: Edge Metadata (Roads) ---
            cursor.execute("DROP TABLE IF EXISTS edge_metadata")
            cursor.execute("""
                CREATE TABLE edge_metadata (
                    sumo_id TEXT PRIMARY KEY,
                    real_name TEXT
                )
            """)
            edge_data = [
                (e.id, e.real_name) for e in edges if e.real_name
            ]
            if edge_data:
                cursor.executemany("INSERT INTO edge_metadata VALUES (?, ?)", edge_data)
            
            # --- Table 3: Data Source Associations ---
            cursor.execute("DROP TABLE IF EXISTS data_associations")
            cursor.execute("""
                CREATE TABLE data_associations (
                    source_name TEXT PRIMARY KEY,
                    source_path TEXT NOT NULL,
                    association_type TEXT NOT NULL,
                    associated_element_id TEXT,
                    file_types_json TEXT
                )
            """)
            
            source_data = [
                (
                    s.name, 
                    s.path, 
                    s.association_type.value, 
                    s.associated_element_id, 
                    json.dumps(s.file_types)
                ) for s in sources
            ]
            
            if source_data:
                cursor.executemany("INSERT INTO data_associations VALUES (?, ?, ?, ?, ?)", source_data)

            # --- Table 4: Raw Data Storage (The "Port of Safety") ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS raw_data_storage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_extension TEXT,
                    import_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    file_hash TEXT,
                    file_size_bytes INTEGER,
                    raw_content BLOB
                )
            """)
            
            # Indexes for Raw Data
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_source ON raw_data_storage(source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_filename ON raw_data_storage(filename)")

            # --- NEW: Specialized Sections (Agnostic Containerization) ---
            # Create a dynamic table for each sensor source registered
            for source in sources:
                source_name = source.name
                # Sanitize the table name (e.g., "Radar Principal" -> "section_radar_principal")
                safe_name = "".join([c if c.isalnum() else "_" for c in source_name]).lower()
                table_name = f"section_{safe_name}"
                
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_timestamp DATETIME NOT NULL,
                        sensor_id TEXT,
                        data_payload JSON NOT NULL,
                        raw_file_reference TEXT
                    )
                """)
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{safe_name}_time ON {table_name}(event_timestamp)")
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{safe_name}_sensor ON {table_name}(sensor_id)")


            conn.commit()


class PersistenceService(QObject):
    """
    Persistence service. Manages the thread pool to save
    the AppState to a .db (SQLite) file.
    """
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self._app_state = app_state 
        self._thread_pool = QThreadPool.globalInstance()
        logging.info("PersistenceService (Service) initialized.")

    @Slot(str)
    def save_configuration(self, file_path: str):
        """
        Starts a PersistenceWorker in a separate thread.
        """
        if not file_path:
            logging.warning("PersistenceService: 'save_configuration' called with empty path.")
            return
            
        if not file_path.endswith(".db"):
            file_path += ".db"
            logging.info(f"PersistenceService: File name corrected to '{file_path}'")

        worker = PersistenceWorker(file_path, self._app_state)
        
        self._thread_pool.start(worker)