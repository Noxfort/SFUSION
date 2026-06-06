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

# File: src/services/etl_service.py
# Author: Gabriel Moraes
# Date: November 2025

import os
import hashlib
import sqlite3
import json
import logging
import zlib
import concurrent.futures
import threading
from datetime import datetime
from PySide6.QtCore import QObject, Slot, QRunnable, QThreadPool, Signal

from src.domain.app_state import AppState
from src.services.extractors import UniversalExtractor
from src.services.neural_transformer import NeuralTransformer

class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(str)

class ETLWorker(QRunnable):
    def __init__(self, db_path: str, app_state: AppState):
        super().__init__()
        self.db_path = db_path
        self._app_state = app_state
        self._is_running = True
        self.signals = WorkerSignals()
        self.db_lock = threading.Lock()

    def _calculate_file_hash(self, file_path: str) -> str:
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logging.error(f"ETLWorker: Failed to hash {file_path}: {e}")
            return ""

    def _get_section_table_name(self, source_name: str) -> str | None:
        if not source_name: return None
        safe_name = "".join([c if c.isalnum() else "_" for c in source_name]).lower()
        return f"section_{safe_name}"

    def _process_sensor_worker(self, source, folder_schema):
        source_name = source.name 
        source_path = source.path
        
        extractor = UniversalExtractor()
        transformer = NeuralTransformer()
        section_table = self._get_section_table_name(source_name)
        
        if not os.path.isdir(source_path):
            return 0, 0
            
        try:
            all_files = []
            for root, _, filenames in os.walk(source_path):
                for f in filenames:
                    all_files.append(os.path.join(root, f))
            files = sorted(all_files)
        except Exception:
            return 0, 0

        local_files = 0
        local_events = 0
        
        conn = None
        try:
            # Use high timeout to wait gracefully for the lock if multiple threads are saving
            conn = sqlite3.connect(self.db_path, timeout=60.0)
            cursor = conn.cursor()
            
            for filename in files:
                if not self._is_running: break

                file_full_path = filename  # filename is now the full absolute path
                filename_only = os.path.basename(file_full_path)
                
                try:
                    file_size = os.path.getsize(file_full_path)
                    _, file_extension = os.path.splitext(filename)
                    file_hash = self._calculate_file_hash(file_full_path)
                    
                    with open(file_full_path, "rb") as f:
                        raw_content = f.read()

                    compressed_content = zlib.compress(raw_content)

                    # Parallel Extraction & Physics Calculation (Releases GIL inside Polars/Numpy)
                    events = []
                    if extractor and section_table:
                        events = extractor.extract(filename, raw_content, source_name)
                        if events:
                            assoc_type_str = getattr(source, 'association_type', "LOCAL")
                            if hasattr(assoc_type_str, 'value'):
                                assoc_type_str = assoc_type_str.value
                            events = transformer.apply_physics(events, folder_schema, assoc_type=assoc_type_str)
                    
                    # Sequential Thread-Safe Database Write
                    with self.db_lock:
                        cursor.execute("""
                            INSERT INTO raw_data_storage (
                                source_id, filename, file_extension, 
                                file_size_bytes, file_hash, raw_content
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            source_name, filename_only, file_extension.lower(), 
                            file_size, file_hash, compressed_content
                        ))
                        
                        local_files += 1

                        if events:
                            for event in events:
                                json_payload = json.dumps(event['data_payload'], default=str)
                                timestamp_str = str(event['event_timestamp'])
                                
                                cursor.execute(f"""
                                    INSERT INTO {section_table} (
                                        event_timestamp, sensor_id, data_payload, raw_file_reference
                                    ) VALUES (?, ?, ?, ?)
                                """, (
                                    timestamp_str, event['sensor_id'], 
                                    json_payload, filename_only
                                ))
                                local_events += 1
                                
                        conn.commit()

                except sqlite3.Error as e:
                    logging.error(f"ETLWorker [Thread {source_name}]: DB Error on {filename_only}: {e}")
                except Exception as e:
                    logging.error(f"ETLWorker [Thread {source_name}]: Error processing {filename_only}: {e}")

        except Exception as e:
            logging.error(f"ETLWorker: Critical Thread Error for {source_name}: {e}")
        finally:
            if conn: conn.close()
            
        return local_files, local_events

    @Slot()
    def run(self):
        logging.info(f"ETLWorker: Starting parallel ingestion (ZLIB) into '{self.db_path}'...")
        
        sources = self._app_state.get_all_data_sources()
        if not sources:
            self.signals.finished.emit()
            return

        transformer = NeuralTransformer()
        
        try:
            transformer.initialize_encoder()
            
            total_files = 0
            total_extracted_events = 0
            
            # =========================================================
            # PASS 1: SCHEMA DISCOVERY (SEQUENTIAL, PROTECTING VRAM)
            # =========================================================
            logging.info("ETLWorker: [PASS 1] Starting SLM Schema Discovery Phase...")
            schema_registry = {}
            
            for source in sources:
                if not self._is_running: break
                
                source_name = source.name 
                source_path = source.path
                
                if not os.path.isdir(source_path): continue
                    
                try:
                    all_files = []
                    for root, _, filenames in os.walk(source_path):
                        for f in filenames:
                            all_files.append(os.path.join(root, f))
                    files = sorted(all_files)
                except Exception: continue
                if not files: continue
                    
                first_file = files[0]
                file_full_path = first_file
                first_file_name = os.path.basename(file_full_path)
                
                try:
                    with open(file_full_path, "rb") as f:
                        raw_content = f.read()
                    
                    raw_text_decoded = raw_content.decode('utf-8', errors='ignore')
                    logging.info(f"ETLWorker: Discovering Schema for '{source_name}' using file '{first_file_name}'")
                    
                    assoc_type_str = getattr(source, 'association_type', "LOCAL")
                    if hasattr(assoc_type_str, 'value'):
                        assoc_type_str = assoc_type_str.value
                    
                    folder_schema = transformer.discover_schema(raw_text_decoded, source_name, assoc_type_str)
                    schema_registry[source_name] = folder_schema
                except Exception as e:
                    logging.error(f"ETLWorker: Failed to discover schema for {source_name}: {e}")
                    schema_registry[source_name] = None
                    
            if not self._is_running: return
            
            # =========================================================
            # PASS 2: PHYSICS MATH & DATABASE INGESTION PHASE (PARALLEL)
            # =========================================================
            logging.info("ETLWorker: [PASS 2] Starting Parallel Math Physics & Ingestion Phase...")
            
            max_threads = max(1, len(sources))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = []
                for source in sources:
                    if not self._is_running: break
                    folder_schema = schema_registry.get(source.name)
                    futures.append(executor.submit(self._process_sensor_worker, source, folder_schema))
                
                for future in concurrent.futures.as_completed(futures):
                    if not self._is_running: break
                    try:
                        f_count, e_count = future.result()
                        total_files += f_count
                        total_extracted_events += e_count
                    except Exception as e:
                        logging.error(f"ETLWorker: Parallel Execution Error: {e}")

            logging.info(
                f"ETLWorker: Complete. {total_files} files ingested. "
                f"{total_extracted_events} events extracted."
            )
            
            self.signals.finished.emit()

        except Exception as e:
            logging.error(f"ETLWorker: Critical Failure: {e}", exc_info=True)
            self.signals.error.emit(str(e))
        finally:
            transformer.cleanup_encoder()

    def stop(self):
        self._is_running = False


class ETLService(QObject):
    """
    Service layer to manage the ETL ingestion process.
    """
    
    # Signal carrying the path of the completed DB
    ingestion_finished = Signal(str)
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self._app_state = app_state
        self._thread_pool = QThreadPool.globalInstance()
        logging.info("ETLService (Service) initialized.")

    @Slot(str)
    def start_ingestion(self, db_path: str):
        if not db_path: return
        
        worker = ETLWorker(db_path, self._app_state)
        
        # Connect Worker signal to Service signal
        # We use a lambda to pass the db_path along with the finished signal
        worker.signals.finished.connect(lambda: self.ingestion_finished.emit(db_path))
        
        self._thread_pool.start(worker)