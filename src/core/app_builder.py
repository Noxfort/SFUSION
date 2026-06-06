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

# File: src/core/app_builder.py
# Author: Gabriel Moraes
# Date: November 2025

import logging
from PySide6.QtWidgets import QMainWindow

# Model and Service Layer
from src.domain.app_state import AppState
from src.services.map_importer import MapImporter
from src.services.data_importer import DataImporter
from src.services.persistence import PersistenceService
from src.services.project_service import ProjectService
from src.services.etl_service import ETLService
from src.services.parquet_service import ParquetService # <--- NEW IMPORT
# Utility Layer
from src.utils.config import ConfigManager
from src.utils.i18n import I18nManager
# View (UI) Layer
from ui.main_window import MainWindow
from ui.map.map_view import MapView
from ui.sources.sources_panel import SourcesPanel
from ui.editor.editor_panel import EditorPanel
# Core/Refactoring Layer
from src.core.map_renderer import MapRenderer
# Controller Layer
from src.main_controller import MainController
from src.controllers.map_controller import MapController
from src.controllers.sources_controller import SourcesController
from src.controllers.info_controller import InfoController
from src.controllers.settings_controller import SettingsController


class AppBuilder:
    """
    Single responsibility: Build and inject all application dependencies
    (Builder Pattern / Dependency Injection).
    """

    def __init__(self):
        # Components will be stored here
        self.config = None
        self.i18n = None
        self.app_state = None
        self.map_importer = None
        self.data_importer = None
        self.persistence_service = None
        self.project_service = None
        self.etl_service = None
        self.parquet_service = None # <--- NEW COMPONENT
        self.main_window = None
        self.map_view = None
        self.sources_panel = None
        self.editor_panel = None
        self.map_renderer = None
        self.main_controller = None
        self.map_controller = None
        self.sources_controller = None
        self.info_controller = None
        self.settings_controller = None

    def build(self) -> QMainWindow:
        """Builds all components and connects them."""
        # 1. Utilities
        self._build_utils()

        # 2. Model and Service Layer (Domain)
        self._build_models()
        self._build_services()

        # 3. View Layer (UI)
        self._build_views()

        # 4. Support Layer (Core/Renderers)
        self._build_renderers()

        # 5. Controller Layer
        self._build_controllers()

        # 6. Final connections
        self._setup_connections()

        self.main_window.set_editor_panel(self.editor_panel) 
        self.main_window.set_map_view(self.map_view)
        self.main_window.set_sources_panel(self.sources_panel)

        return self.main_window

    def _build_utils(self):
        self.config = ConfigManager("config/settings.json")
        self.config.load_config() 

        locale_path = self.config.get("locale_path")
        language = self.config.get("language")

        if not locale_path or not language:
            logging.critical("Critical Configuration Error!")
            config_path = self.config.config_path 
            logging.critical(f"  File: {config_path}")
            logging.critical("  The 'locale_path' and 'language' keys are missing or null.")
            logging.critical("  Please check your 'config/settings.json'.")
            raise ValueError(
                f"Configuration 'locale_path' or 'language' not found in {config_path}"
            )
        
        self.i18n = I18nManager(locale_path, language) 

    def _build_models(self):
        self.app_state = AppState()

    def _build_services(self):
        self.map_importer = MapImporter(self.app_state)
        self.data_importer = DataImporter(self.app_state)
        self.persistence_service = PersistenceService(self.app_state)
        self.project_service = ProjectService(self.app_state)
        self.etl_service = ETLService(self.app_state)
        self.parquet_service = ParquetService() # <--- INSTANTIATION

    def _build_views(self):
        self.main_window = MainWindow(self.i18n)
        self.map_view = MapView(self.main_window)
        self.sources_panel = SourcesPanel(self.i18n, self.main_window)
        self.editor_panel = EditorPanel(self.i18n, self.main_window) 

    def _build_renderers(self):
        self.map_renderer = MapRenderer(self.map_view, self.app_state, self.config)

    def _build_controllers(self):
        
        self.info_controller = InfoController(
            self.app_state, 
            self.editor_panel,
            self.map_renderer, 
            self.i18n
        )

        self.map_controller = MapController(
            self.app_state, 
            self.map_renderer,
            self.info_controller
        )

        # UPDATED: Passing parquet_service to MainController
        self.main_controller = MainController(
            self.main_window,
            self.map_importer,
            self.data_importer,
            self.persistence_service,
            self.project_service,
            self.etl_service, 
            self.parquet_service, # <--- INJECTION
            self.i18n
        )

        self.sources_controller = SourcesController(
            self.app_state, 
            self.sources_panel, 
            self.i18n
        )
        
        self.settings_controller = SettingsController(
            self.main_window,
            self.config,
            self.i18n
        )

    def _setup_connections(self):
        """Connects all signals and slots."""
        
        # Connects toolbar actions
        self.main_controller.setup_connections()
        
        # Connects the "Generate .db" button from the side panel
        self.sources_panel.save_config_requested.connect(
            self.main_controller._on_save_config
        )
        
        # Connects the MainWindow signal to the SettingsController slot
        self.main_window.settings_requested.connect(
            self.settings_controller.show_settings_dialog
        )

        # Connects other controllers
        self.map_controller.setup_connections(self.map_view)
        self.sources_controller.setup_connections()
        self.info_controller.setup_connections()
        
        # Connects the "Savable" state signal
        self.app_state.savable_state_changed.connect(
            self.main_window.set_savable_state
        )
        self.app_state.savable_state_changed.connect(
            self.sources_panel.set_savable_state
        )