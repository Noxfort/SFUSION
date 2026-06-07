# SFusion (SYNAPSE Fusion) Mapper - "Day Zero" ETL Configuration Tool
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/services/extractors.py
# Author: Gabriel Moraes
# Date: November 2025

import json
import csv
import io
import logging
from src.utils.i18n import backend_i18n
from datetime import datetime
from typing import List, Dict, Any

class BaseExtractor:
    """Base class for the universal extractor."""
    def extract(self, filename: str, raw_content: bytes, source_name: str = "") -> List[Dict[str, Any]]:
        raise NotImplementedError

class UniversalExtractor(BaseExtractor):
    """ 
    UNIVERSAL Source: Agnostic JSON/CSV parser for any sensor. 
    Obeys SOLID (OCP/SRP). Extracts rows unconditionally and injects 
    implicit flow counting to let the SLMEngine map the schema.
    """
    def extract(self, filename: str, raw_content: bytes, source_name: str = "") -> List[Dict[str, Any]]:
        results = []
        try:
            text = raw_content.decode('utf-8', errors='ignore')
            sensor_id = source_name if source_name else "generic_sensor"
            
            # Extract timestamp from file modified time as a fallback
            try:
                timestamp = datetime.now()
            except Exception:
                timestamp = datetime.now()

            # --- Attempt JSON Parsing ---
            try:
                data = json.loads(text)
                events = []
                
                if isinstance(data, list):
                    events = data
                elif isinstance(data, dict):
                    # Find ALL arrays inside the JSON and merge them. 
                    # This prevents extracting only 'alerts' and missing 'jams' in Waze.
                    events = []
                    for key, val in data.items():
                        if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                            events.extend(val)
                    
                    if not events:
                        # If no nested list, treat the root dict as a single event
                        events = [data]
                
                for ev in events:
                    if not isinstance(ev, dict): continue
                    
                    # Try to find a local timestamp field if possible
                    ev_ts = timestamp
                    for ts_key in ['timestamp', 'time', 'date', 'pubMillis', 'event_timestamp']:
                        if ts_key in ev:
                            try:
                                val = ev[ts_key]
                                if isinstance(val, (int, float)):
                                    # Assume unix millis if large, else seconds
                                    if val > 1e11: ev_ts = datetime.fromtimestamp(val / 1000.0)
                                    else: ev_ts = datetime.fromtimestamp(val)
                                elif isinstance(val, str):
                                    ev_ts = datetime.fromisoformat(val.replace('Z', '+00:00'))
                            except Exception:
                                pass
                            break
                            
                    payload = ev.copy()
                    
                    results.append({
                        "event_timestamp": ev_ts,
                        "sensor_id": sensor_id,
                        "data_payload": payload
                    })
                return results
                
            except json.JSONDecodeError:
                pass # Fallback to CSV

            # --- Attempt CSV Parsing ---
            f = io.StringIO(text)
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    payload = dict(row)
                    
                    results.append({
                        "event_timestamp": timestamp,
                        "sensor_id": sensor_id,
                        "data_payload": payload
                    })
                except Exception:
                    continue

        except Exception as e:
            logging.error(f"UniversalExtractor: {backend_i18n.t('errors.extractors.processing_failed', file=filename, error=str(e))}")
            
        return results
