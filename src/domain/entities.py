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

# File: src/domain/entities.py
# Author: Gabriel Moraes
# Date: November 2025

from dataclasses import dataclass, field
from enum import Enum
import uuid
from typing import List, Tuple, Any



class AssociationType(str, Enum):
    """ Defines how a DataSource is associated with the map. """
    UNASSOCIATED = "UNASSOCIATED"
    GLOBAL = "GLOBAL"
    LOCAL = "LOCAL"


@dataclass
class DataSource:
    """
    Entity (Model) representing a single data source.
    """
    path: str
    
    # Display name for the data source
    name: str
    
    # List of detected file types (e.g., ["JSON", "CSV"])
    file_types: list[str] = field(default_factory=list)
    

    id: str = field(default_factory=lambda: f"src_{uuid.uuid4().hex[:8]}")
    parser_id: str | None = None
    
    association_type: AssociationType = AssociationType.UNASSOCIATED
    
    # Generic element ID (can be a node or edge)
    associated_element_id: str | None = None
    



@dataclass
class MapNode:
    """
    Entity (Model) representing a single map node (junction).
    """
    id: str
    x: float
    y: float
    

    node_type: str = "unknown"
    

    real_name: str | None = None


@dataclass
class MapEdge:
    """
    Entity (Model) representing a single map edge (road).
    """
    id: str
    

    from_node: str
    to_node: str
    shape: List[Tuple[float, float]] = field(default_factory=list)
    

    real_name: str | None = None