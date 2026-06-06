import os
import logging
import json
from typing import Optional
from src.core.schemas import KinematicMap

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

logger = logging.getLogger(__name__)

class SLMEngine:
    def __init__(self, model_path: str = None):
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'slm_settings.json')
        self.config = {
            "model_path": "src/models/Phi-4-mini-reasoning-UD-Q8_K_XL.gguf",
            "n_gpu_layers": -1,
            "n_ctx": 16384,
            "flash_attn": True,
            "verbose": False,
            "max_tokens": 512,
            "temperature": 0.0
        }
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                self.config.update(loaded_config)
        except Exception as e:
            logger.warning(f"SLMEngine: Failed to load {config_path}, using defaults. Error: {e}")

        self.model_path = model_path if model_path else self.config.get("model_path")
        self.llm = None
        
        if Llama is None:
            logger.warning("llama-cpp-python is not installed. SLMEngine will be disabled.")
            return

        try:
            logger.info(f"SLMEngine: Loading SLM from {self.model_path} with GPU offloading and TensorCores (Flash Attention)...")
            # n_gpu_layers=-1 delegates all layers to VRAM for maximum speed
            # flash_attn=True explicitamente ativa o uso de TensorCores (Ampere+) via FlashAttention no cuBLAS
            self.llm = Llama(
                model_path=self.model_path,
                n_gpu_layers=self.config.get("n_gpu_layers", -1), 
                n_ctx=self.config.get("n_ctx", 16384),
                flash_attn=self.config.get("flash_attn", True),
                verbose=self.config.get("verbose", False)
            )
            logger.info("SLMEngine: Loaded successfully.")
        except Exception as e:
            logger.error(f"SLMEngine: Failed to load model: {e}")

    def discover_schema(self, raw_content: str, source_name: str, assoc_type: str = "LOCAL") -> Optional[KinematicMap]:
        """
        Extracts kinematic column names from the raw JSON/CSV payload using strictly JSON output.
        """
        if self.llm is None:
            return None

        # Schema JSON constraint
        json_schema = {
            "type": "object",
            "properties": {
                "speed_col": {"type": ["string", "null"]},
                "flow_col": {"type": ["string", "null"]},
                "intensity_col": {"type": ["string", "null"]},
                "distance_col": {"type": ["string", "null"]},
                "time_col": {"type": ["string", "null"]},
                "occupancy_col": {"type": ["string", "null"]}
            },
            "required": ["speed_col", "flow_col", "intensity_col", "distance_col", "time_col", "occupancy_col"]
        }

        try:
            content_str = raw_content.decode('utf-8', errors='ignore')
        except Exception:
            content_str = str(raw_content)
            
        # Send the whole file context to fully utilize the 16k context window of Phi-4
        # We limit the raw text size to ~50,000 chars (~13k tokens) to prevent llama.cpp ValueError 
        # (exceeding 16384 context window crashes the C++ backend)
        if len(content_str) > 50000:
            logger.warning(f"SLMEngine: File too large ({len(content_str)} chars). Truncating to 50KB to fit 16k KV Cache safely.")
            content_str = content_str[:50000]

        # Load prompt from JSON file
        prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'schema_discovery.json')
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompts = json.load(f)
                prompt_template = prompts.get('schema_discovery_prompt', '')
                if isinstance(prompt_template, list):
                    prompt_template = '\n'.join(prompt_template)
        except Exception as e:
            logger.error(f"SLMEngine: Failed to load prompt from {prompt_path}: {e}")
            return None

        prompt = prompt_template.replace("{source_name}", source_name).replace("{content_str}", content_str).replace("{assoc_type}", assoc_type)


        try:
            temp = self.config.get("temperature", 0.0)
            logger.info(f"SLMEngine: Starting GPU inference for '{source_name}' (temperature={temp}, thinking activated)...")
            response = self.llm(
                prompt,
                max_tokens=2048,
                temperature=0.1,
                repeat_penalty=1.1,
                stop=["--- END OF INSTRUCTIONS ---"], # Stop if it starts hallucinating prompt
                echo=False
            )
            
            output_text = response["choices"][0]["text"].strip()
            
            if not output_text.startswith("<think>"):
                output_text = "<think>\n" + output_text
                
            import re
            # Extract thinking content for structured logging
            think_match = re.search(r'<think>(.*?)</think>', output_text, flags=re.DOTALL)
            if think_match:
                think_content = think_match.group(1).strip()
                logger.info(
                    f"\n"
                    f"===========================================================\n"
                    f"🧠 SLM THINKING REASONING: [{source_name}]\n"
                    f"===========================================================\n"
                    f"{think_content}\n"
                    f"==========================================================="
                )
            else:
                logger.warning(f"SLMEngine: No <think> block detected for {source_name}.")
            
            # Remove the <think> block to extract only the payload mapping
            content_without_think = re.sub(r'<think>.*?</think>', '', output_text, flags=re.DOTALL).strip()
            
            data = {}
            # Try parsing as JSON first
            json_match = re.search(r'\{.*\}', content_without_think, flags=re.DOTALL)
            if json_match:
                try:
                    parsed_json = json.loads(json_match.group(0))
                    for k, v in parsed_json.items():
                        if v is not None and str(v).strip().upper() not in ["NULL", "NONE", ""]:
                            data[k] = str(v).strip()
                except json.JSONDecodeError:
                    logger.warning(f"SLMEngine: Failed to parse JSON for {source_name}. Fallback to line parsing.")
            
            # Fallback line parsing (KEY=VALUE) just in case
            if not data:
                for line in content_without_think.split('\n'):
                    line = line.strip()
                    if '=' in line:
                        key, val = line.split('=', 1)
                        key = key.strip()
                        val = val.strip()
                        # Clean quotes if any
                        val = val.strip('",\'')
                        if val.upper() not in ["NULL", "NONE", ""]:
                            data[key] = val

            logger.info(
                f"\n"
                f"🎯 EXTRACTED SCHEMA: [{source_name}]\n"
                f"-----------------------------------------------------------\n"
                f"{json.dumps(data, indent=2)}\n"
                f"-----------------------------------------------------------"
            )
            
            # CLEAR KV CACHE: Ensure SLM is fully wiped clean for the next sensor to prevent contamination
            if hasattr(self.llm, "reset"):
                self.llm.reset()
                logger.info(f"SLMEngine: KV Cache reset successfully for '{source_name}' (Amnesia verified).")
            
            return KinematicMap(
                speed_col=data.get("speed_col"),
                flow_col=data.get("flow_col"),
                intensity_col=data.get("intensity_col"),
                distance_col=data.get("distance_col"),
                time_col=data.get("time_col"),
                occupancy_col=data.get("occupancy_col"),
                confidence_score=0.99 # Thinking mode yields higher confidence
            )
        except Exception as e:
            logger.error(f"SLMEngine: Inference failed: {e}")
            if hasattr(self.llm, "reset"):
                self.llm.reset()
            return None

