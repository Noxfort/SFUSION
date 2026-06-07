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

# File: src/core/schemas.py
# Author: Gabriel Moraes
# Date: May 2026

from pydantic import BaseModel, Field
from typing import Optional
from src.utils.i18n import backend_i18n

class KinematicMap(BaseModel):
    """
    Strongly Typed Object acting as a Mathematical Blueprint.
    The SLM (Phi-4-mini) will instantiate this object filling it with the actual columns
    identified in the sensor sample so the Vector Engine (Polars) can build the AST.
    """
    
    # --- Direct Variables ---
    speed_col: Optional[str] = Field(
        None, 
        description=backend_i18n.t("schemas.desc_speed")
    )
    flow_col: Optional[str] = Field(
        None, 
        description=backend_i18n.t("schemas.desc_flow")
    )
    intensity_col: Optional[str] = Field(
        None, 
        description=backend_i18n.t("schemas.desc_intensity")
    )

    # --- Base Kinematic Variables (for Derivation) ---
    distance_col: Optional[str] = Field(
        None, 
        description=backend_i18n.t("schemas.desc_distance")
    )
    time_col: Optional[str] = Field(
        None, 
        description=backend_i18n.t("schemas.desc_time")
    )
    occupancy_col: Optional[str] = Field(
        None, 
        description=backend_i18n.t("schemas.desc_occupancy")
    )

    # --- Confidence Metadata ---
    confidence_score: Optional[float] = Field(
        None,
        description=backend_i18n.t("schemas.desc_confidence")
    )

