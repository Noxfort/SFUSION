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

# File: src/services/project_service.py
# Author: Gabriel Moraes
# Date: November 2025

import logging
from src.utils.i18n import backend_i18n
import json
import dataclasses
from enum import Enum
from PySide6.QtCore import QObject, Slot, QRunnable, QThreadPool

from src.domain.app_state import AppState
from src.domain.entities import MapNode, MapEdge, DataSource, AssociationType


class ProjectDataEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle dataclasses and Enums."""
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


class ProjectSaveWorker(QRunnable):
    """Worker to save the project .json in a separate thread."""
    
    def __init__(self, file_path: str, app_state: AppState):
        super().__init__()
        self.file_path = file_path
        self._app_state = app_state 

    @Slot()
    def run(self):
        """Executes the save logic."""
        logging.info(backend_i18n.t("project.save.worker.init", path=self.file_path))
        try:
            # 1. Get all data from AppState
            nodes = self._app_state.get_all_nodes()
            edges = self._app_state.get_all_edges()
            sources = self._app_state.get_all_data_sources()
            
            # 2. Create a state dictionary
            state_data = {
                "nodes": nodes,
                "edges": edges,
                "data_sources": sources
            }
            
            # 3. Save as JSON
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, cls=ProjectDataEncoder, indent=2)
            
            logging.info(backend_i18n.t("project.save.worker.success", path=self.file_path))

        except Exception as e:
            logging.error(f"ProjectSaveWorker: {backend_i18n.t('project.save.worker.error', error=str(e))}", exc_info=True)


class ProjectLoadWorker(QRunnable):
    """Worker to load the project .json in a separate thread."""
    
    def __init__(self, file_path: str, app_state: AppState):
        super().__init__()
        self.file_path = file_path
        self._app_state = app_state 

    @Slot()
    def run(self):
        """Executes the load logic."""
        logging.info(backend_i18n.t("project.load.worker.init", path=self.file_path))
        try:
            # 1. Read the JSON file
            with open(self.file_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            # 2. Recreate Nodes and Edges
            nodes = [MapNode(**data) for data in state_data.get("nodes", [])]
            edges = [MapEdge(**data) for data in state_data.get("edges", [])]
            
            # 3. Recreate Data Sources
            sources = []
            for data in state_data.get("data_sources", []):
                # Convert the string back to the Enum
                try:
                    data["association_type"] = AssociationType(data["association_type"])
                except ValueError:
                    data["association_type"] = AssociationType.UNASSOCIATED
                sources.append(DataSource(**data))

            # 4. Clear old state and load the new one
            # (IMPORTANT: Clear sources first, then the map)
            
            # Clear old sources (iterate over a copy to avoid errors)
            for s in self._app_state.get_all_data_sources()[:]:
                self._app_state.delete_data_source(s.path)
            
            # Load the new map (this clears the old map)
            self._app_state.set_map_data(nodes, edges)
            
            # Add new sources
            for s in sources:
                self._app_state.add_data_source(s)
            
            logging.info(backend_i18n.t("project.load.worker.success", path=self.file_path))

        except Exception as e:
            logging.error(f"ProjectLoadWorker: {backend_i18n.t('project.load.worker.error', error=str(e))}", exc_info=True)


class ProjectService(QObject):
    """
    Project management service. Manages the thread pool to
    save and load AppState to/from a .sfm.json file.
    """
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self._app_state = app_state 
        self._thread_pool = QThreadPool.globalInstance()
        logging.info(backend_i18n.t("project.init"))

    @Slot(str)
    def save_project(self, file_path: str):
        """
        Starts a ProjectSaveWorker in a separate thread.
        """
        if not file_path:
            logging.warning(f"ProjectService: {backend_i18n.t('project.save.no_path')}")
            return
            
        if not file_path.endswith(".sfm.json"):
            file_path += ".sfm.json"

        worker = ProjectSaveWorker(file_path, self._app_state)
        self._thread_pool.start(worker)

    @Slot(str)
    def load_project(self, file_path: str):
        """
        Starts a ProjectLoadWorker in a separate thread.
        """
        if not file_path:
            logging.warning(f"ProjectService: {backend_i18n.t('project.load.no_path')}")
            return

        worker = ProjectLoadWorker(file_path, self._app_state)
        self._thread_pool.start(worker)