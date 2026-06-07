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

# File: src/agent/slm_output_parser.py
# Author: Gabriel Moraes
# Date: June 2026
# Description:
#    Robust output parser for SLM inference results.
#    Extracts structured JSON schema maps and thinking content from raw LLM output,
#    regardless of whether the model emits proper <think>...</think> tags.

import json
import re
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SLMOutputParser:
    """
    Stateless parser that separates SLM raw output into two components:
      1. Thinking content (reasoning text for logging/debugging)
      2. Schema data (the JSON kinematic mapping)

    Handles edge cases where the SLM omits <think> or </think> tags
    by scanning for the last balanced JSON block in the output.
    """

    @staticmethod
    def extract_last_json(text: str) -> dict:
        """
        Scans from the end of the text to find the last balanced {...} block
        and parses it as JSON. The schema map is always the last JSON object
        emitted by the SLM, so scanning backwards is the most reliable strategy.
        """
        end_idx = text.rfind('}')
        if end_idx == -1:
            return {}
        depth = 0
        for i in range(end_idx, -1, -1):
            if text[i] == '}':
                depth += 1
            elif text[i] == '{':
                depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[i:end_idx + 1])
                except json.JSONDecodeError:
                    return {}
        return {}

    @staticmethod
    def extract_thinking(text: str) -> str:
        """
        Extracts the thinking/reasoning content from the SLM output.
        First tries proper <think>...</think> tags, then falls back to
        treating everything before the last JSON block as thinking.
        """
        # Case A: Proper <think>...</think> tags exist
        think_match = re.search(r'<think>(.*?)</think>', text, flags=re.DOTALL)
        if think_match:
            return think_match.group(1).strip()

        # Case B: No closing </think> — extract everything before the last JSON block
        last_brace = text.rfind('}')
        if last_brace != -1:
            depth = 0
            json_start = last_brace
            for i in range(last_brace, -1, -1):
                if text[i] == '}':
                    depth += 1
                elif text[i] == '{':
                    depth -= 1
                if depth == 0:
                    json_start = i
                    break
            think_content = text[:json_start].strip()
        else:
            think_content = text.strip()

        # Clean any stray <think> tags from the thinking content
        think_content = re.sub(r'</?think>', '', think_content).strip()
        return think_content

    @staticmethod
    def build_schema_data(parsed_json: dict) -> Dict[str, str]:
        """
        Filters the parsed JSON into a clean schema dictionary,
        discarding null/none/empty values and normalizing strings.
        """
        data = {}
        for k, v in parsed_json.items():
            if v is not None and str(v).strip().upper() not in ["NULL", "NONE", ""]:
                data[k] = str(v).strip()
        return data

    @staticmethod
    def fallback_line_parse(text: str) -> Dict[str, str]:
        """
        Last-resort parser for KEY=VALUE format output.
        Used when JSON extraction fails entirely.
        """
        data = {}
        # Strip any tags and JSON blocks for line parsing
        cleaned = re.sub(r'</?think>', '', text)
        cleaned = re.sub(r'\{[^}]*\}', '', cleaned, flags=re.DOTALL)
        for line in cleaned.split('\n'):
            line = line.strip()
            if '=' in line:
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('",\'')
                if val.upper() not in ["NULL", "NONE", ""]:
                    data[key] = val
        return data

    @classmethod
    def parse(cls, raw_output: str) -> Tuple[str, Dict[str, str]]:
        """
        Main entry point. Parses raw SLM output into (thinking_content, schema_data).
        
        Returns:
            Tuple of (thinking_content: str, schema_data: dict)
        """
        # Step 1: Extract JSON
        parsed_json = cls.extract_last_json(raw_output)
        
        # Step 2: Extract thinking
        thinking = cls.extract_thinking(raw_output)
        
        # Step 3: Build schema data from JSON
        data = cls.build_schema_data(parsed_json) if parsed_json else {}
        
        # Step 4: Fallback to line parsing if JSON failed
        if not data:
            logger.warning("SLMOutputParser: JSON extraction failed. Attempting KEY=VALUE fallback.")
            data = cls.fallback_line_parse(raw_output)
        
        return thinking, data
