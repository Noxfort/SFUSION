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

# File: src/services/map_importer.py
# Author: Gabriel Moraes
# Date: November 2025

import logging
import gzip
from lxml import etree
from PySide6.QtCore import QObject, Slot, QRunnable, QThreadPool, Signal

from src.domain.app_state import AppState
from src.domain.entities import MapNode, MapEdge

class MapImportWorker(QRunnable):
    """
    Worker to import the map in a separate thread
    to avoid blocking the UI.
    """
    def __init__(self, file_path: str, app_state: AppState):
        super().__init__()
        self.file_path = file_path
        self._app_state = app_state

    @Slot()
    def run(self):
        """Executes the map import."""
        logging.info(f"MapImportWorker: Starting import of '{self.file_path}'...")
        try:
            nodes, edges = self._parse_net_xml(self.file_path)
            
            if not nodes and not edges:
                logging.warning(f"MapImportWorker: File '{self.file_path}' contained no nodes or edges.")
            
            self._app_state.set_map_data(nodes, edges)
            
            logging.info(f"MapImportWorker: Import complete. {len(nodes)} nodes, {len(edges)} edges.")

        except etree.XMLSyntaxError as e:
            logging.error(f"MapImportWorker: XML syntax error reading '{self.file_path}': {e}")
        except Exception as e:
            logging.error(f"MapImportWorker: Unexpected error importing map: {e}", exc_info=True)

    def _parse_net_xml(self, file_path):
        """Reads the .net.xml (or .net.xml.gz) file and extracts data."""
        
        open_func = gzip.open if file_path.endswith('.gz') else open
        
        with open_func(file_path, 'rb') as f:
            parser = etree.XMLParser(target=NetXMLParserTarget())
            etree.parse(f, parser)
            
            return parser.target.nodes, parser.target.edges


class NetXMLParserTarget(object):
    """
    Target for the lxml parser. Called incrementally
    as XML is read. (Saves significant memory)
    """
    def __init__(self):
        self.nodes = []
        self.edges = []
        self._current_edge = None

    def start(self, tag, attrib):
        """Called when a <tag> is opened."""
        try:
            if tag == "junction" and attrib.get("type") != "internal":
                node = MapNode(
                    id=attrib["id"],
                    x=float(attrib["x"]),
                    y=float(attrib["y"]),
                    node_type=attrib.get("type", "unknown"),
                    real_name=None 
                )
                self.nodes.append(node)

            elif tag == "edge" and not attrib.get("function") == "internal":
                self._current_edge = {
                    "id": attrib["id"],
                    "from_node": attrib["from"],
                    "to_node": attrib["to"],
                    "shape": []
                }
            
            elif tag == "lane" and self._current_edge is not None:
                shape_str = attrib.get("shape")
                if shape_str:
                    points = [
                        (float(p.split(',')[0]), float(p.split(',')[1]))
                        for p in shape_str.split(' ')
                    ]
                    # Only the first lane defines the geometry
                    if not self._current_edge["shape"]:
                        self._current_edge["shape"] = points

        except KeyError as e:
            logging.warning(f"NetXMLParserTarget: Missing attribute in XML: {e} (Tag: {tag}, Attrs: {attrib})")
        except Exception as e:
            logging.error(f"NetXMLParserTarget: Error in 'start' (Tag: {tag}): {e}")


    def end(self, tag):
        """Called when a </tag> is closed."""
        if tag == "edge" and self._current_edge is not None:
            if self._current_edge["shape"]:
                edge = MapEdge(
                    id=self._current_edge["id"],
                    from_node=self._current_edge["from_node"],
                    to_node=self._current_edge["to_node"],
                    shape=self._current_edge["shape"],
                    real_name=None
                )
                self.edges.append(edge)
            
            self._current_edge = None

    def data(self, data):
        pass

    def close(self):
        return "Parsing finished"


class MapImporter(QObject):
    """
    Map import service. Manages the thread pool.
    """
    
    def __init__(self, app_state: AppState):
        super().__init__()
        self._app_state = app_state
        self._thread_pool = QThreadPool.globalInstance()
        logging.info("MapImporter (Service) initialized.")

    @Slot(str)
    def load_map(self, file_path: str):
        """
        Starts a MapImportWorker in a separate thread to load the map.
        """
        if not file_path:
            logging.warning("MapImporter: 'load_map' called with empty path.")
            return

        worker = MapImportWorker(file_path, self._app_state)
        self._thread_pool.start(worker)