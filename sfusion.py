#!/usr/bin/env python3
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

# File: sfusion.py
# Author: Gabriel Moraes
# Date: November 2025

import sys
import os
import signal
import logging
import logging.handlers
from PySide6.QtWidgets import QApplication

# --- Path Configuration ---
# Defines the application root directory (APP_ROOT)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Adds 'src' and 'ui' directories to sys.path
# This allows Python to find modules (e.g., from src.core...)
sys.path.append(os.path.join(APP_ROOT, 'src'))
sys.path.append(os.path.join(APP_ROOT, 'ui'))

# --- Component Imports (after path configuration) ---
from src.core.app_builder import AppBuilder


def setup_logging():
    """Configures the global logging system."""
    
    # Log message format
    log_format = (
        "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s] "
        "%(message)s (%(filename)s:%(lineno)d)"
    )
    
    # Log level: INFO for general messages, DEBUG for details
    log_level = logging.INFO 

    # Basic logging configuration
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)  # Sends logs to console
        ]
    )
    
    # File logging configuration (SFusion Root)
    try:
        log_file = os.path.join(APP_ROOT, "sfusion.log")
        # Rotates the log: 5 files of 5MB each
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=(5*1024*1024), backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(log_format))
        # Ensure utf-8 encoding for file output
        file_handler.encoding = 'utf-8'
        logging.getLogger().addHandler(file_handler)
    except Exception as e:
        logging.warning(f"Could not write to {log_file}. File logging disabled: {e}")


def main():
    """Main function: Initializes and runs the application."""
    
    # 1. Configure logging BEFORE anything else
    setup_logging()
    logging.info(f"Starting SFusion Mapper... (APP_ROOT: {APP_ROOT})")

    # Hard Kill handler for Ctrl+C in terminal (stops PySide6 event loop from blocking)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # 2. Create the Qt application
    app = QApplication(sys.argv)

    # 3. Use the AppBuilder to construct the application
    # The AppBuilder builds everything internally (Window, Models, Controllers)
    try:
        builder = AppBuilder()
        main_window = builder.build()
        
        # 4. Show the main window
        main_window.show()
        logging.info("Application started successfully.")

        # 5. Run the application event loop
        
        # Ensure all background C++ and Polars threads are killed when closing
        app.aboutToQuit.connect(lambda: os._exit(0))
        
        sys.exit(app.exec())

    except Exception as e:
        # Fatal error during initialization
        logging.critical(f"Critical failure building the application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()