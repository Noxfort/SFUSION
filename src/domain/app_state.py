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

# File: src/domain/app_state.py
# Author: Gabriel Moraes
# Date: November 2025

import logging
from PySide6.QtCore import QObject, Signal 
from .entities import MapNode, MapEdge, DataSource, AssociationType


class AppState(QObject):
    """
    Stores the current application state in memory.
    Acts as the Single Source of Truth.
    Emits signals when data changes.
    """
    
    map_data_loaded = Signal()
    data_sources_changed = Signal(list) 
    data_association_changed = Signal(str, str)
    association_mode_changed = Signal(bool)
    savable_state_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        
        self._nodes: list[MapNode] = []
        self._edges: list[MapEdge] = []
        self._nodes_by_id: dict[str, MapNode] = {}
        self._edges_by_id: dict[str, MapEdge] = {}

        self._data_sources: list[DataSource] = []
        self._sources_by_path: dict[str, DataSource] = {}
        
        self._selected_source_path: str | None = None
        self._is_in_association_mode: bool = False

        self._current_savable_state: bool = False

    
    def _is_savable(self) -> bool:
        """
        Checks if the current application state is valid for saving.
        Rule 1: The map must be loaded.
        Rule 2: All LOCAL sources must be associated.
        """
        if not self._nodes:
            logging.debug("AppState: Not savable (map not loaded).")
            return False
            
        for source in self._data_sources:
            if (source.association_type == AssociationType.LOCAL and
                source.associated_element_id is None):
                logging.debug(f"AppState: Not savable (local source '{source.name}' not associated).")
                return False

        logging.debug("AppState: State is savable.")
        return True

    def _check_and_emit_savable_state(self):
        """
        Checks the current state and emits 'savable_state_changed'
        ONLY if the state has changed.
        """
        is_valid = self._is_savable()
        if is_valid != self._current_savable_state:
            self._current_savable_state = is_valid
            self.savable_state_changed.emit(is_valid)
            
    # --- Map Methods ---

    def set_map_data(self, nodes: list[MapNode], edges: list[MapEdge]):
        self._nodes = nodes
        self._edges = edges
        self._nodes_by_id = {node.id: node for node in nodes}
        self._edges_by_id = {edge.id: edge for edge in edges}
        logging.info(f"AppState: Map data updated. {len(nodes)} nodes, {len(edges)} edges.")
        self.map_data_loaded.emit()
        self._check_and_emit_savable_state() 

    def get_all_nodes(self) -> list[MapNode]:
        return self._nodes

    def get_all_edges(self) -> list[MapEdge]:
        return self._edges

    def get_node_by_id(self, node_id: str) -> MapNode | None:
        return self._nodes_by_id.get(node_id)

    def get_edge_by_id(self, edge_id: str) -> MapEdge | None:
        return self._edges_by_id.get(edge_id)

    def get_edge_pair_id(self, edge_id: str) -> str | None:
        """
        Finds the ID of the edge "pair" (forward/reverse).
        This is the only pair-related function in AppState.
        """
        pair_id = ""
        if edge_id.startswith("-"):
            pair_id = edge_id[1:]
        else:
            pair_id = f"-{edge_id}"
        
        if pair_id in self._edges_by_id:
            return pair_id
        
        return None

    def update_element_real_name(self, element_id: str, real_name: str):
        element = self.get_node_by_id(element_id) or self.get_edge_by_id(element_id)
        if element:
            element.real_name = real_name if real_name else None
            logging.info(f"AppState: 'real_name' updated for '{element_id}'")
        else:
            logging.warning(f"AppState: Attempted to update unknown element: '{element_id}'")

    # --- Data Source Methods ---

    def add_data_source(self, source: DataSource):
        if source.path in self._sources_by_path:
            logging.warning(f"AppState: Data source '{source.path}' already exists.")
            return
        self._data_sources.append(source)
        self._sources_by_path[source.path] = source
        self.data_sources_changed.emit(self._data_sources)
        self._check_and_emit_savable_state() 

    def get_all_data_sources(self) -> list[DataSource]:
        return self._data_sources

    def get_data_source_by_id(self, source_id: str) -> DataSource | None:
        return self._sources_by_path.get(source_id)

    def set_selected_data_source(self, source_id: str | None):
        self._selected_source_path = source_id
        if not source_id:
            self.exit_association_mode()

    def update_selected_source_association_type(self, assoc_type: str):
        source = self._get_selected_source()
        if source:
            try:
                source.association_type = AssociationType(assoc_type.upper())
                source.associated_element_id = None
                
                logging.info(f"AppState: Association of '{source.name}' set to '{assoc_type}'.")
                self.data_association_changed.emit(source.path, source.association_type.value)
                self._check_and_emit_savable_state() 
            except ValueError:
                logging.error(f"AppState: Attempted to set invalid type: {assoc_type}")

    # --- Association Mode Logic ---
    
    def _get_selected_source(self) -> DataSource | None:
        if not self._selected_source_path:
            return None
        return self.get_data_source_by_id(self._selected_source_path)

    def is_in_association_mode(self) -> bool:
        return self._is_in_association_mode

    def enter_association_mode(self):
        if self._is_in_association_mode:
            return
        if not self._selected_source_path:
            logging.warning("AppState: Attempted to enter association mode without a selected source.")
            return
            
        source = self._get_selected_source()
        if source and source.associated_element_id:
            logging.warning(f"AppState: Source '{source.name}' already associated. Cancel the association first.")
            self.set_selected_data_source(None) 
            return

        self._is_in_association_mode = True
        self.association_mode_changed.emit(True)
        logging.info("AppState: Association mode ENABLED.")

    def exit_association_mode(self):
        if not self._is_in_association_mode:
            return
        self._is_in_association_mode = False
        self.association_mode_changed.emit(False)
        logging.info("AppState: Association mode DISABLED.")

    def associate_selected_source_to_element(self, element_id: str):
        source = self._get_selected_source()
        if not source:
            logging.error("AppState: Attempted to associate, but no source was selected.")
            self.exit_association_mode()
            return
        
        ids_to_associate = [element_id]
        
        if self.get_edge_by_id(element_id):
            pair_id = self.get_edge_pair_id(element_id)
            if pair_id:
                ids_to_associate.append(pair_id)
        
        # Simplified logic - associates only to the first clicked ID
        # DataSource entity only supports a single association
        e_id_to_associate = ids_to_associate[0]
        
        if source.associated_element_id:
             logging.warning(f"AppState: Source '{source.name}' was already associated. Ignoring.")
        else:
            source.associated_element_id = e_id_to_associate
            source.association_type = AssociationType.LOCAL 
            
            logging.info(f"AppState: Source '{source.name}' associated to element '{e_id_to_associate}'.")
            self.data_association_changed.emit(source.path, e_id_to_associate)

        self.exit_association_mode()
        self._check_and_emit_savable_state() 

    # --- Source Management Methods ---

    def delete_data_source(self, source_id: str):
        source = self._sources_by_path.get(source_id)
        if not source:
            logging.warning(f"AppState: Attempted to delete unknown source: {source_id}")
            return

        self._data_sources.remove(source)
        del self._sources_by_path[source_id]
        logging.info(f"AppState: Data source '{source.name}' removed.")

        if self._selected_source_path == source_id:
            self.set_selected_data_source(None)
        self.data_sources_changed.emit(self._data_sources)
        self._check_and_emit_savable_state() 

    def toggle_source_association_type(self, source_id: str):
        source = self.get_data_source_by_id(source_id)
        if not source:
            return

        if source.association_type == AssociationType.GLOBAL:
            source.association_type = AssociationType.LOCAL
        else:
            source.association_type = AssociationType.GLOBAL
        
        source.associated_element_id = None
        logging.info(f"AppState: Association of '{source.name}' changed to '{source.association_type.value}'.")
        self.data_association_changed.emit(source.path, source.association_type.value)
        self._check_and_emit_savable_state() 

    # --- EditorPanel Methods ---

    def get_sources_associated_with_element(self, element_id: str) -> list[DataSource]:
        """
        Returns sources associated with THIS exact element.
        Pair logic has been moved to the Controllers.
        """
        sources = []
        for source in self._data_sources:
            # Checks only the exact ID
            if source.associated_element_id == element_id:
                sources.append(source)
        return sources

    def get_available_local_sources(self, current_element_id: str) -> list[DataSource]:
        """
        Returns local sources that are free (or already associated with this element).
        Pair logic has been moved to the Controllers.
        """
        available = []
        
        for source in self._data_sources:
            if source.association_type == AssociationType.LOCAL:
                # Checks only the exact ID
                if source.associated_element_id is None or source.associated_element_id == current_element_id:
                    available.append(source)
        return available

    def set_element_associations(self, element_id: str, new_source_ids: list[str]):
        """
        Sets associations (via Checkbox) for a SINGLE element.
        """
        
        new_ids_set = set(new_source_ids)
        
        current_sources = self.get_sources_associated_with_element(element_id)
        current_ids_set = {s.path for s in current_sources}

        ids_to_add = new_ids_set - current_ids_set
        ids_to_remove = current_ids_set - new_ids_set
        
        has_changed = False
        
        for source_id in ids_to_remove:
            source = self.get_data_source_by_id(source_id)
            if source:
                source.associated_element_id = None
                logging.info(f"AppState: Source '{source.name}' released from '{element_id}'.")
                self.data_association_changed.emit(source.path, "LOCAL") 
                has_changed = True
        
        for source_id in ids_to_add:
            source = self.get_data_source_by_id(source_id)
            if source:
                if source.associated_element_id and source.associated_element_id != element_id:
                    logging.warning(f"AppState: Source '{source.name}' moved from '{source.associated_element_id}' to '{element_id}'.")
                
                source.associated_element_id = element_id
                source.association_type = AssociationType.LOCAL  # Ensures correct type
                
                logging.info(f"AppState: Source '{source.name}' associated to '{element_id}' (via Editor).")
                self.data_association_changed.emit(source.path, element_id)
                has_changed = True
        
        if has_changed:
            self._check_and_emit_savable_state()