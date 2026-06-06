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

# File: src/controllers/map_controller.py
# Author: Gabriel Moraes
# Date: November 2025

import logging
from PySide6.QtCore import QObject, Slot, Qt

from src.domain.app_state import AppState
from src.core.map_renderer import MapRenderer
from src.controllers.info_controller import InfoController
from ui.map.map_view import MapView


class MapController(QObject):
    """
    Controller for the map. Manages click interactions
    and delegates drawing and information display.
    Highlights edge "pairs" (forward/reverse).
    """

    def __init__(
        self,
        app_state: AppState,
        map_renderer: MapRenderer,
        info_controller: InfoController,
    ):
        super().__init__()
        self._app_state = app_state
        self._map_renderer = map_renderer
        self._info_controller = info_controller
        self._map_view = None
        
        self._current_selected_element_id: str | None = None

    def setup_connections(self, map_view: MapView):
        """Connects MapView signals to this controller's slots."""
        self._map_view = map_view
        
        map_view.nodeClicked.connect(self._on_node_clicked)
        map_view.edgeClicked.connect(self._on_edge_clicked)
        map_view.emptySpaceClicked.connect(self._on_empty_space_clicked)

        self._app_state.map_data_loaded.connect(self.draw_map)
        self._app_state.association_mode_changed.connect(
            self._on_association_mode_changed
        )
        
        self._app_state.data_association_changed.connect(
            self._on_association_updated
        )

    # --- Click Logic ---

    @Slot(str)
    def _on_node_clicked(self, node_id: str):
        """Called when a node (QGraphicsItem) is clicked."""
        
        self._map_renderer.clear_highlight()
        
        if self._app_state.is_in_association_mode():
            logging.info(f"MapController: Associating source to Node '{node_id}'.")
            self._app_state.associate_selected_source_to_element(node_id)
        
        else:
            self._current_selected_element_id = node_id
            
            # Check if the node has associated data
            sources_list = self._app_state.get_sources_associated_with_element(node_id)
            is_associated = (len(sources_list) > 0)
            
            self._map_renderer.highlight_element(node_id, is_associated)

            logging.info(f"MapController: Showing editor for Node '{node_id}'.")
            node = self._app_state.get_node_by_id(node_id)
            if node:
                self._info_controller.show_for_node(node)
            else:
                logging.warning(f"MapController: Node ID '{node_id}' not found in AppState.")

    @Slot(str)
    def _on_edge_clicked(self, edge_id: str):
        """
        Called when an edge (QGraphicsItem) is clicked.
        Highlights both the edge and its pair.
        """
        
        self._map_renderer.clear_highlight()
        
        if self._app_state.is_in_association_mode():
            logging.info(f"MapController: Associating source to Edge '{edge_id}'.")
            self._app_state.associate_selected_source_to_element(edge_id)
            
        else:
            self._current_selected_element_id = edge_id
            
            # A. Find the "pair" (e.g., "-123")
            pair_id = self._app_state.get_edge_pair_id(edge_id)
            
            # B. Check association status (Green or Red)
            #    Check sources for the clicked ID
            sources_list = self._app_state.get_sources_associated_with_element(edge_id)
            #    Check sources for the pair, if it exists
            if pair_id:
                sources_list.extend(
                    self._app_state.get_sources_associated_with_element(pair_id)
                )
            
            # If either road has sources, the entire road is "associated"
            is_associated = (len(sources_list) > 0)

            # C. Highlight the clicked edge (e.g., "123")
            self._map_renderer.highlight_element(edge_id, is_associated)

            # D. Highlight the "pair" (e.g., "-123") with the SAME color
            if pair_id:
                self._map_renderer.highlight_element(pair_id, is_associated)

            logging.info(f"MapController: Showing editor for Edge '{edge_id}'.")
            edge = self._app_state.get_edge_by_id(edge_id)
            if edge:
                self._info_controller.show_for_edge(edge)
            else:
                logging.warning(f"MapController: Edge ID '{edge_id}' not found in AppState.")

    @Slot()
    def _on_empty_space_clicked(self):
        """Called when empty space on the map is clicked."""
        logging.info("MapController: Empty space clicked.")
        
        self._current_selected_element_id = None
        
        self._info_controller.hide_panel()  # This also clears the highlight
        self._app_state.exit_association_mode()

    # --- Slots (Listen to Model) ---

    @Slot(bool)
    def _on_association_mode_changed(self, is_active: bool):
        """Called by AppState. Changes the map cursor."""
        if not self._map_view:
            return
        if is_active:
            self._map_view.setCursor(Qt.CrossCursor)
        else:
            self._map_view.setCursor(Qt.ArrowCursor)

    @Slot(str, str)
    def _on_association_updated(self, source_id: str, element_or_type: str):
        """
        Called by AppState when an association changes.
        Updates the aura if the affected element is the selected one.
        Highlights the pair as well.
        """
        
        current_ids = { self._current_selected_element_id }
        pair_id = None
        if self._current_selected_element_id and self._app_state.get_edge_by_id(self._current_selected_element_id):
            pair_id = self._app_state.get_edge_pair_id(self._current_selected_element_id)
            if pair_id:
                current_ids.add(pair_id)
        
        # If the changed element is one of the currently selected
        # (the clicked ID OR its pair)
        if element_or_type in current_ids:
            logging.debug(f"MapController: Updating aura for element {element_or_type}.")
            
            # Re-check the association status (Green or Red)
            sources_list = self._app_state.get_sources_associated_with_element(self._current_selected_element_id)
            if pair_id:
                 sources_list.extend(
                    self._app_state.get_sources_associated_with_element(pair_id)
                )
            is_associated = (len(sources_list) > 0)
            
            # Clear old highlight
            self._map_renderer.clear_highlight()
            
            # Re-apply highlight (which will now be Red)
            self._map_renderer.highlight_element(self._current_selected_element_id, is_associated)
            if pair_id:
                self._map_renderer.highlight_element(pair_id, is_associated)


    @Slot()
    def draw_map(self):
        """
        Delegates map rendering to the MapRenderer.
        """
        logging.info("MapController: Delegating 'draw_map' to MapRenderer.")
        self._map_renderer.draw_map()