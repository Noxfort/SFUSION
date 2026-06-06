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

# File: src/services/data_importer.py
# Author: Gabriel Moraes
# Date: November 2025

import os
import logging
import pandas as pd
from PySide6.QtCore import QObject, Slot, QRunnable, QThreadPool, Signal

from src.domain.app_state import AppState
from src.domain.entities import DataSource, AssociationType


class DataImportWorker(QRunnable):
    """
    Worker to analyze a data source folder.
    """
    
    def __init__(self, folder_path: str, app_state: AppState, assoc_type: str):
        super().__init__()
        self.folder_path = folder_path
        self._app_state = app_state
        self.assoc_type = assoc_type  # "GLOBAL" or "LOCAL" (uppercase)
        self.signals = QObject() 

    @Slot()
    def run(self):
        """
        Analyzes the folder, identifies file types and updates AppState.
        """
        logging.info(f"DataImportWorker: Analyzing '{self.folder_path}'...")
        try:
            file_types = self._analyze_folder(self.folder_path)
            
            if not file_types:
                logging.warning(f"DataImportWorker: No valid data sources found in {self.folder_path}")
                return

            try:
                assoc_enum = AssociationType(self.assoc_type)
            except ValueError:
                logging.error(f"DataImportWorker: Unknown association type '{self.assoc_type}'. Using UNASSOCIATED.")
                assoc_enum = AssociationType.UNASSOCIATED

            new_source = DataSource(
                path=self.folder_path,
                name=os.path.basename(self.folder_path),
                file_types=file_types,
                association_type=assoc_enum,
                associated_element_id=None
            )
            
            self._app_state.add_data_source(new_source)
            
            logging.info(f"DataImportWorker: Analysis complete for {self.folder_path}. Types: {file_types}")

        except Exception as e:
            logging.error(f"DataImportWorker: Failed to analyze {self.folder_path}: {e}", exc_info=True)

    def _analyze_folder(self, folder_path):
        """Scans the folder and returns the supported file types."""
        types = set()
        try:
            for file_name in os.listdir(folder_path):
                file_lower = file_name.lower()
                
                if file_lower.endswith((".csv", ".csv.gz")):
                    types.add("CSV")
                elif file_lower.endswith((".json", ".json.gz")):
                    types.add("JSON")
                elif file_lower.endswith((".xml", ".xml.gz")):
                    if not file_lower.endswith(".net.xml") and not file_lower.endswith(".net.xml.gz"):
                        types.add("XML")
                elif file_lower.endswith((".xls", ".xlsx")):
                    types.add("Excel")
        except FileNotFoundError:
            logging.error(f"DataImportWorker: Folder not found: {folder_path}")
            return []
        except NotADirectoryError:
            logging.error(f"DataImportWorker: Path is not a directory: {folder_path}")
            return []
            
        return list(types)


class DataImporter(QObject):
    """
    Service for importing data sources. Manages the thread pool.
    """
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self._app_state = app_state 
        self._thread_pool = QThreadPool.globalInstance()
        logging.info("DataImporter (Service) initialized.")

    @Slot(str, str)
    def add_data_source(self, folder_path: str, assoc_type: str):
        """
        Starts a DataImportWorker in a separate thread.
        """
        if not folder_path or not os.path.isdir(folder_path):
            logging.warning(f"DataImporter: Invalid folder path provided: '{folder_path}'")
            return

        worker = DataImportWorker(folder_path, self._app_state, assoc_type) 
        self._thread_pool.start(worker)