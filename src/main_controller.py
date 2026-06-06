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

# File: src/main_controller.py
# Author: Gabriel Moraes
# Date: November 2025

import logging
import os
from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QFileDialog, QMessageBox

from ui.main_window import MainWindow
from src.services.map_importer import MapImporter
from src.services.data_importer import DataImporter
from src.services.persistence import PersistenceService
from src.services.project_service import ProjectService
from src.services.etl_service import ETLService 
from src.services.parquet_service import ParquetService
from src.utils.i18n import I18nManager


class MainController(QObject):
    """
    Main controller. Manages toolbar actions (View)
    and orchestrates Services (Services).
    """

    def __init__(
        self,
        main_window: MainWindow,
        map_importer: MapImporter,
        data_importer: DataImporter,
        persistence_service: PersistenceService,
        project_service: ProjectService,
        etl_service: ETLService, 
        parquet_service: ParquetService,
        i18n: I18nManager
    ):
        super().__init__()
        
        self._view = main_window
        self._map_importer = map_importer
        self._data_importer = data_importer
        self._persistence = persistence_service
        self._project = project_service
        self._etl = etl_service
        self._parquet = parquet_service
        self._i18n = i18n

        self._current_path = os.path.expanduser("~")
        
        # State variables for the pipeline
        self._temp_db_path = None
        self._target_parquet_path = None
        
        logging.info("MainController (Controller) initialized.")

    def setup_connections(self):
        """Connects the MainWindow signals to this controller's slots."""
        
        # Project & Map Connections
        self._view.open_project_requested.connect(self._on_open_project)
        self._view.save_project_requested.connect(self._on_save_project)
        self._view.open_map_requested.connect(self._on_open_map)
        self._view.add_source_requested.connect(self._on_add_source)
        
        # The Trigger Button
        self._view.save_config_requested.connect(self._on_save_config)

        # --- PIPELINE CHAIN ---
        # 1. ETL Finished -> Start Parquet
        self._etl.ingestion_finished.connect(self._on_ingestion_finished)
        
        # 2. Parquet Finished -> Delete Temp DB
        self._parquet.export_finished.connect(self._on_export_finished)

    # --- Private Slots (Listen to View) ---

    @Slot()
    def _on_open_project(self):
        t = self._i18n.t
        file_path, _ = QFileDialog.getOpenFileName(
            self._view, t("dialog.open_project.title"), self._current_path, t("dialog.open_project.filter")
        )
        if file_path:
            self._current_path = os.path.dirname(file_path)
            try:
                self._project.load_project(file_path)
                self._view.show_status_message(f"Project '{os.path.basename(file_path)}' loaded.")
            except Exception as e:
                self._view.show_error_message(t("dialog.error.title"), t("dialog.error.generic_load", error=str(e)))

    @Slot()
    def _on_save_project(self):
        t = self._i18n.t
        file_path, _ = QFileDialog.getSaveFileName(
            self._view, t("dialog.save_project.title"), self._current_path, t("dialog.save_project.filter")
        )
        if file_path:
            self._current_path = os.path.dirname(file_path)
            try:
                self._project.save_project(file_path)
                self._view.show_status_message(f"Project '{os.path.basename(file_path)}' saved.")
            except Exception as e:
                self._view.show_error_message(t("dialog.error.title"), t("dialog.error.generic_save", error=str(e)))
    
    @Slot()
    def _on_open_map(self):
        t = self._i18n.t
        file_path, _ = QFileDialog.getOpenFileName(
            self._view, t("dialog.open_map.title"), self._current_path, t("dialog.open_map.filter")
        )
        if file_path:
            self._current_path = os.path.dirname(file_path)
            try:
                self._map_importer.load_map(file_path)
                self._view.show_status_message(t("main_window.status_map_loaded", name=os.path.basename(file_path)))
            except Exception as e:
                self._view.show_error_message(t("dialog.error.title"), t("dialog.error.generic_load", error=str(e)))

    @Slot()
    def _on_add_source(self):
        t = self._i18n.t
        folder_path = QFileDialog.getExistingDirectory(self._view, t("dialog.add_source.title"), self._current_path)
        if not folder_path: return
            
        self._current_path = folder_path
        
        msg_box = QMessageBox(self._view)
        msg_box.setWindowTitle(t("dialog.add_source.type_title"))
        msg_box.setText(t("dialog.add_source.type_text", name=os.path.basename(folder_path)))
        global_btn = msg_box.addButton(t("dialog.add_source.type_global"), QMessageBox.YesRole)
        local_btn = msg_box.addButton(t("dialog.add_source.type_local"), QMessageBox.NoRole)
        msg_box.addButton(QMessageBox.Cancel)
        msg_box.exec()
        
        clicked = msg_box.clickedButton()
        assoc_type = "GLOBAL" if clicked == global_btn else "LOCAL" if clicked == local_btn else None
        
        if assoc_type:
            try:
                self._data_importer.add_data_source(folder_path, assoc_type)
                self._view.show_status_message(t("main_window.status_source_added", name=os.path.basename(folder_path)))
            except Exception as e:
                self._view.show_error_message(t("dialog.error.title"), t("dialog.error.generic_load", error=str(e)))

    @Slot()
    def _on_save_config(self):
        """
        Triggered by UI Button (Generate Dataset).
        NOW ASKS FOR PARQUET, BUT CREATES HIDDEN DB FIRST.
        """
        t = self._i18n.t
        # Change filter to suggest Parquet
        file_path, _ = QFileDialog.getSaveFileName(
            self._view,
            "Save Traffic Dataset", # Could be i18n
            self._current_path,
            "Parquet Dataset (*.parquet)"
        )
        
        if file_path:
            if not file_path.endswith(".parquet"):
                file_path += ".parquet"

            self._current_path = os.path.dirname(file_path)
            self._target_parquet_path = file_path
            
            # Create a hidden temp DB name based on the target filename
            base_name = os.path.basename(file_path)
            self._temp_db_path = os.path.join(self._current_path, f".temp_sfusion_{base_name}.db")

            logging.info(f"MainController: Pipeline init. Target: {self._target_parquet_path}, Staging: {self._temp_db_path}")

            try:
                # Lock UI to prevent multiple clicks
                self._view.set_savable_state(False)
                if self._view.sources_panel:
                    self._view.sources_panel.set_savable_state(False)

                # Step 1: Save Schema to TEMP DB
                self._persistence.save_configuration(self._temp_db_path)
                
                # Step 2: Start ETL on TEMP DB
                self._etl.start_ingestion(self._temp_db_path)
                
                self._view.show_status_message("Processing Raw Data (Staging)...")
                
            except Exception as e:
                # Unlock UI if there is an error
                self._view.set_savable_state(True)
                if self._view.sources_panel:
                    self._view.sources_panel.set_savable_state(True)
                self._view.show_error_message(t("dialog.error.title"), str(e))

    @Slot(str)
    def _on_ingestion_finished(self, db_path: str):
        """Automated Step 3: Trigger Parquet Export to the user's path."""
        logging.info("MainController: Staging complete. Exporting to final Parquet...")
        self._view.show_status_message("Optimizing & Exporting to Parquet...")
        
        # Use the stored target path
        try:
            self._parquet.export_db_to_parquet(db_path, self._target_parquet_path)
        except Exception as e:
            self._view.set_savable_state(True)
            if self._view.sources_panel:
                self._view.sources_panel.set_savable_state(True)
            self._view.show_error_message(self._i18n.t("dialog.error.title"), str(e))

    @Slot()
    def _on_export_finished(self):
        """Automated Step 4: Cleanup."""
        logging.info("MainController: Export complete. Cleaning up staging DB...")
        
        if self._temp_db_path and os.path.exists(self._temp_db_path):
            try:
                os.remove(self._temp_db_path)
                logging.info(f"MainController: Deleted temp file {self._temp_db_path}")
            except OSError as e:
                logging.warning(f"MainController: Failed to delete temp DB: {e}")

        final_name = os.path.basename(self._target_parquet_path) if self._target_parquet_path else "File"
        self._view.show_status_message(f"Success! Generated: {final_name}")
        
        # Unlock UI when finished
        self._view.set_savable_state(True)
        if self._view.sources_panel:
            self._view.sources_panel.set_savable_state(True)
        
        QMessageBox.information(self._view, "Success", f"Traffic Dataset generated successfully:\n{self._target_parquet_path}")