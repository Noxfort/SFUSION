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

# File: src/controllers/sources_controller.py
# Author: Gabriel Moraes
# Date: November 2025

import logging
from PySide6.QtCore import QObject, Slot, Qt

from src.domain.app_state import AppState
from ui.sources.sources_panel import SourcesPanel
from src.utils.i18n import I18nManager, backend_i18n
from src.domain.entities import DataSource


class SourcesController(QObject):
    """
    Controller for the SourcesPanel.
    
    Responsibilities:
    - Listen to AppState (Model) and update the View list.
    - Listen to the View (list selection and menu) and update AppState (Model).
    """
    
    def __init__(
        self,
        app_state: AppState,
        view: SourcesPanel,
        i18n: I18nManager
    ):
        """
        Initializes the controller.
        
        :param app_state: The Single Source of Truth.
        :param view: The View (SourcesPanel) managed by this controller.
        :param i18n: The internationalization manager.
        """
        super().__init__() 
        
        self._app_state = app_state
        self._view = view
        self._i18n = i18n
        
        logging.info(backend_i18n.t("controller.sources.init"))

    def setup_connections(self):
        """Connects Model and View signals."""
        
        # Left-click connections
        self._view.source_selection_changed.connect(
            self._on_source_selected
        )
        
        # Right-click context menu connections
        self._view.source_delete_requested.connect(
            self._on_source_delete
        )
        self._view.source_modify_type_requested.connect(
            self._on_source_modify_type
        )
        
        # Model to View connections
        self._app_state.data_sources_changed.connect(
            self._on_model_sources_updated
        )
        self._app_state.data_association_changed.connect(
            self._on_model_association_updated
        )

    # --- Private Slots (Listen to View) ---

    @Slot(str)
    def _on_source_selected(self, source_id: str):
        """Called by View (left-click). Updates the Model."""
        self._app_state.set_selected_data_source(source_id)
        
        source = self._app_state.get_data_source_by_id(source_id)
        if source:
            # Updates the radio display (informational)
            # .value gets the string ("GLOBAL" or "LOCAL") from the Enum
            self._view.set_association_type(source.association_type.value)
        else:
            self._view.set_association_type("LOCAL")  # Default

    # --- Context Menu Slots ---

    @Slot(str)
    def _on_source_delete(self, source_id: str):
        """Called by View (right-click -> Delete). Updates the Model."""
        logging.info(backend_i18n.t("controller.sources.delete", id=source_id))
        self._app_state.delete_data_source(source_id)

    @Slot(str)
    def _on_source_modify_type(self, source_id: str):
        """Called by View (right-click -> Modify). Updates the Model."""
        logging.info(backend_i18n.t("controller.sources.modify", id=source_id))
        self._app_state.toggle_source_association_type(source_id)

    # --- Private Slots (Listen to Model) ---
    
    @Slot(list)
    def _on_model_sources_updated(self, sources_list: list[DataSource]):
        """Called by AppState. Updates the list in the View."""
        self._view.update_sources_list(sources_list)

    @Slot(str, str)
    def _on_model_association_updated(self, source_id: str, assoc_type_or_id: str):
        """Called by AppState. Updates the radios in the View."""
        
        current_view_selection = self._view.sources_list_widget.currentItem()
        if current_view_selection:
            current_selected_id = current_view_selection.data(Qt.UserRole)
            if current_selected_id == source_id:
                
                if assoc_type_or_id.upper() in ["GLOBAL", "LOCAL"]:
                    self._view.set_association_type(assoc_type_or_id)