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

# File: src/core/map_renderer.py
# Author: Gabriel Moraes
# Date: November 2025

import logging
# Required imports for map drawing
from PySide6.QtGui import QPen, QBrush, QColor, QPainterPath, QPainterPathStroker
from PySide6.QtCore import Qt, Slot, QPointF
from PySide6.QtWidgets import QGraphicsItem 

from ui.map.map_view import MapView
from src.domain.app_state import AppState
from src.utils.config import ConfigManager


class MapRenderer:
    """
    Single responsibility: Draw the map (Nodes and Edges)
    on the MapView (QGraphicsScene).
    Supports additive highlighting.
    """

    def __init__(
        self,
        map_view: MapView,
        app_state: AppState,
        config: ConfigManager,
    ):
        self._view = map_view
        self._scene = map_view.scene 
        self._app_state = app_state

        self._drawable_items_by_id: dict[str, list[QGraphicsItem]] = {}
        self._current_highlight: list[QGraphicsItem] = []
        
        self._zoom_config = config.get("map_zoom", {})
        self._min_zoom = self._zoom_config.get("min", 0.1)
        self._max_zoom = self._zoom_config.get("max", 10.0)

        self._colors = config.get("map_colors", {})
        
        self._edge_color = QColor(self._colors.get("edge", "#4A4A4A"))
        self._node_color = QColor(self._colors.get("node", "#E74C3C"))
        
        self._sel_assoc_color = QColor(self._colors.get("selection_associated", "#E74C3C")) 
        self._sel_free_color = QColor(self._colors.get("selection_free", "#2ECC71")) 

        bg_color = self._colors.get("background", "#FFFFFF")
        self._scene.setBackgroundBrush(QColor(bg_color))

        # --- Pens - For Nodes and Highlights ---
        
        # Node (Junction) - SOLID (scales with zoom)
        pen_node = QPen(self._node_color, 1, Qt.SolidLine)
        
        # Node Highlights (Solid)
        pen_node_assoc = QPen(self._sel_assoc_color, 2, Qt.SolidLine)
        pen_node_free = QPen(self._sel_free_color, 2, Qt.SolidLine)

        self._pens = {
            "node": pen_node,
            "selected_node_assoc": pen_node_assoc,
            "selected_node_free": pen_node_free
        }

        # --- Brushes (Fill) ---
        self._brushes = {
            # Node Fill
            "node": QBrush(self._node_color),
            "selected_node_assoc": QBrush(self._sel_assoc_color),
            "selected_node_free": QBrush(self._sel_free_color),
            
            # Edge (Road) Fill
            "edge": QBrush(self._edge_color),
            "selected_edge_assoc": QBrush(self._sel_assoc_color),
            "selected_edge_free": QBrush(self._sel_free_color)
        }

    def draw_map(self):
        """Reads data from AppState and draws the map on the scene."""
        logging.info("MapRenderer: Reading map data from AppState...")
        self._scene.clear()
        
        self._drawable_items_by_id.clear()
        self._current_highlight.clear()
        
        nodes = self._app_state.get_all_nodes()
        edges = self._app_state.get_all_edges()

        if not nodes and not edges:
            logging.warning("MapRenderer: No map data to draw.")
            return
        
        # Draw ROADS first (they stay in the background)
        edge_count = 0
        for edge in edges:
            self._draw_edge(edge)
            edge_count += 1

        # Draw NODES after (they stay on top)
        node_count = 0
        for node in nodes:
            if node.node_type == "internal":
                continue
            self._draw_node(node)
            node_count += 1
            
        logging.info(f"MapRenderer: Map drawn. {node_count} nodes, {edge_count} (of {len(edges)}) edges rendered.")

        self._view.fit_map_in_view()
        self._view.set_zoom_limits(self._min_zoom, self._max_zoom)


    def _draw_edge(self, edge):
        """
        Draws the edge as a polygon (ribbon) with width
        using QPainterPathStroker.
        """
        if len(edge.shape) < 2:
            return 

        # 1. Create the central line path
        path = QPainterPath()
        start_point = edge.shape[0]
        path.moveTo(QPointF(start_point[0], -start_point[1]))
        
        for point in edge.shape[1:]:
            path.lineTo(QPointF(point[0], -point[1]))

        # 2. Create the Stroker to transform line into polygon
        stroker = QPainterPathStroker()
        stroker.setWidth(3.2)  # Width in meters
        stroker.setCapStyle(Qt.FlatCap)
        
        # 3. Generate the polygon (ribbon)
        stroke_path = stroker.createStroke(path)

        # 4. Set appearance (No outline, solid fill)
        pen = QPen(Qt.NoPen)
        brush = self._brushes["edge"]

        # 5. Add the polygon (QGraphicsPathItem) to the scene
        item = self._scene.addPath(stroke_path, pen, brush)
        
        item.setData(0, "edge")
        item.setData(1, edge.id)
        item.setZValue(0)  # Z=0 (Roads in background)
        
        self._drawable_items_by_id.setdefault(edge.id, []).append(item)

    def _draw_node(self, node):
        """Draws a single node (junction) on the scene."""
        
        pen = self._pens["node"]
        brush = self._brushes["node"]
        
        r = 7  # Radius in world coordinates
        
        ellipse = self._scene.addEllipse(-r, -r, 2 * r, 2 * r, pen, brush)
        ellipse.setPos(node.x, -node.y)
        ellipse.setData(0, "node")
        ellipse.setData(1, node.id)
        ellipse.setZValue(1)  # Z=1 (Nodes on top)
        
        self._drawable_items_by_id.setdefault(node.id, []).append(ellipse)

    # --- Highlight Method ---

    @Slot(str, bool)
    def highlight_element(self, element_id: str | None, is_associated: bool):
        """
        Adds an element (Node or Edge) to the current highlight.
        Does NOT clear the previous highlight (additive).
        
        :param element_id: The ID of the element to highlight.
        :param is_associated: True (Red) if it already has data, False (Green) if free.
        """
        
        # The MapController is now responsible for clearing highlights.
        
        if not element_id:
            return

        items_to_highlight = self._drawable_items_by_id.get(element_id)
        if not items_to_highlight:
            logging.warning(f"MapRenderer: Could not find item '{element_id}' to highlight.")
            return

        color_key = "assoc" if is_associated else "free"
        
        for item in items_to_highlight:
            item_type = item.data(0)
            
            if item_type == "node":
                item.setPen(self._pens[f"selected_node_{color_key}"])
                item.setBrush(self._brushes[f"selected_node_{color_key}"])
                item.setZValue(3) 
            
            elif item_type == "edge":
                item.setBrush(self._brushes[f"selected_edge_{color_key}"])
                item.setPen(Qt.NoPen)
                item.setZValue(2) 
            
            # Add item to highlight list (to be cleared later)
            self._current_highlight.append(item)

    @Slot()
    def clear_highlight(self):
        """Restores highlighted items back to their normal appearance."""
        if not self._current_highlight:
            return

        for item in self._current_highlight:
            item_type = item.data(0)
            
            if item_type == "node":
                item.setPen(self._pens["node"])
                item.setBrush(self._brushes["node"])
                item.setZValue(1) 
            
            elif item_type == "edge":
                item.setBrush(self._brushes["edge"])
                item.setPen(Qt.NoPen)
                item.setZValue(0)
        
        self._current_highlight.clear()