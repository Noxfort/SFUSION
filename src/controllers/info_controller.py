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

# File: src/controllers/info_controller.py
# Author: Gabriel Moraes
# Date: November 2025

import logging
from PySide6.QtCore import QObject, Slot

from src.domain.app_state import AppState
from src.domain.entities import MapNode, MapEdge
from src.utils.i18n import I18nManager
from ui.editor.editor_panel import EditorPanel
from src.core.map_renderer import MapRenderer


class InfoController(QObject):
    """
    Controller for the EditorPanel.
    
    Responsibilities:
    - Listen to EditorPanel (View) signals.
    - Update AppState (Model) when 'Save' is clicked
      (and apply changes to the edge "pair", if one exists).
    - Manage multiple local source associations (Checkboxes).
    - Orchestrate panel show/hide.
    - Command highlight (aura) clearing in MapRenderer.
    """
    
    def __init__(
        self,
        app_state: AppState,
        view: EditorPanel,
        map_renderer: MapRenderer,
        i18n: I18nManager
    ):
        super().__init__() 
        
        self._app_state = app_state
        self._view = view
        self._map_renderer = map_renderer
        self._i18n = i18n
        
        self._current_element = None

    def setup_connections(self):
        """Connects View signals to this controller's slots."""
        self._view.save_clicked.connect(self._on_save)
        self._view.close_clicked.connect(self.hide_panel)

    # --- Public Methods (Called by MapController) ---

    @Slot(MapNode)
    def show_for_node(self, node: MapNode):
        """Displays the panel with Node data."""
        self._current_element = node
        self._prepare_view_data() 
        
        t = self._i18n.t
        self._view.show_data(
            title=t("info_panel.title_node"),
            sumo_id=node.id,
            real_name=node.real_name
        )
        self._view.show()
        self._view.raise_()

    @Slot(MapEdge)
    def show_for_edge(self, edge: MapEdge):
        """Displays the panel with Edge data."""
        self._current_element = edge
        self._prepare_view_data() 
        
        t = self._i18n.t
        self._view.show_data(
            title=t("info_panel.title_edge"),
            sumo_id=edge.id,
            real_name=edge.real_name
        )
        self._view.show()
        self._view.raise_()

    @Slot()
    def hide_panel(self):
        """
        Hides the panel, clears the current element AND clears the highlight.
        """
        self._current_element = None
        self._view.hide()
        self._map_renderer.clear_highlight()


    # --- Private Helper Methods ---

    def _prepare_view_data(self):
        """
        Gets available sources and current associations (for the element AND its pair)
        and updates the View (QListWidget with checkboxes).
        """
        if not self._current_element:
            return

        element_id = self._current_element.id

        # 1. Get available local sources
        # (Free sources + sources already associated with THIS element)
        available_sources = self._app_state.get_available_local_sources(element_id)

        # 2. Check which sources are already associated with this element
        current_source_ids = set()
        sources = self._app_state.get_sources_associated_with_element(element_id)
        for s in sources:
            current_source_ids.add(s.path)
        
        # 3. Pass lists to the View
        self._view.update_sources_list(available_sources, current_source_ids)


    # --- Private Slots (Listen to View) ---

    @Slot(str)
    def _on_save(self, new_real_name: str):
        """
        Called when the 'Save' button in the View is clicked.
        Saves Real Name for the pair and consolidates associations.
        """
        if not self._current_element:
            logging.warning("InfoController: 'Save' clicked, but no element was selected.")
            return

        element_id = self._current_element.id
        pair_id = None
        
        # --- Action 1: Save Real Name (for both) ---
        
        ids_to_name = {element_id}
        if isinstance(self._current_element, MapEdge):
            pair_id = self._app_state.get_edge_pair_id(element_id)
            if pair_id:
                ids_to_name.add(pair_id)
        
        for e_id in ids_to_name:
            logging.debug(f"InfoController: Saving name '{new_real_name}' for ID {e_id}")
            self._app_state.update_element_real_name(
                e_id, 
                new_real_name
            )
            
        # --- Action 2: Save Associations (Only for clicked ID) ---
        
        selected_source_ids = self._view.get_selected_source_ids()
        
        logging.info(f"InfoController: Saving associations {selected_source_ids} for ID {element_id}")
        self._app_state.set_element_associations(
            element_id, 
            selected_source_ids
        )
        
        self.hide_panel()