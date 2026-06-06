import re
from src.agent.slm_engine import SLMEngine

engine = SLMEngine()

content = b"""
{
  "estimated_speed_kmh": 60,
  "volume": 1200
}
"""

raw_content_str = content.decode()

import os
import json
prompt_path = os.path.join(os.path.dirname('src/agent/slm_engine.py'), 'src/prompts/schema_discovery.json')
with open(prompt_path, 'r', encoding='utf-8') as f:
    prompts = json.load(f)
    prompt_template = prompts.get('schema_discovery_prompt', '')
    if isinstance(prompt_template, list):
        prompt_template = '\n'.join(prompt_template)

prompt = prompt_template.replace("{source_name}", "cam").replace("{content_str}", raw_content_str)

response = engine.llm(
    prompt,
    max_tokens=512,
    temperature=0.0
)

output_text = response["choices"][0]["text"].strip()
print("RAW OUTPUT TEXT:")
print(repr(output_text))

