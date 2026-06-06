import json
import logging
from src.services.neural_transformer import NeuralTransformer

with open('/home/gabriel-moraes/Documentos/output_2/waze/waze_feed_20260608_000000.json') as f:
    waze_events = json.load(f).get("jams", [])

transformer = NeuralTransformer()
transformer.initialize_encoder()

waze_json_str = json.dumps(waze_events[0] if waze_events else {})

engine = transformer.slm_engine
prompt_path = 'src/prompts/schema_discovery.json'
with open(prompt_path, 'r', encoding='utf-8') as f:
    prompts = json.load(f)
    prompt_template = prompts.get('schema_discovery_prompt', '')
    if isinstance(prompt_template, list):
        prompt_template = '\n'.join(prompt_template)

prompt = prompt_template.replace("{source_name}", "waze").replace("{content_str}", waze_json_str)

response = engine.llm(
    prompt,
    max_tokens=1024,
    temperature=0.0
)

output_text = response["choices"][0]["text"].strip()
with open("test_waze_out.txt", "w") as outf:
    outf.write(output_text)

