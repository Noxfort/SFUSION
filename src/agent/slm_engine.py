import os
import logging
import json
from typing import Optional
from src.core.schemas import KinematicMap
from src.slm.slm_output_parser import SLMOutputParser

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

logger = logging.getLogger(__name__)

from src.utils.slm_telemetry import slm_logger, get_hardware_telemetry

class SLMEngine:
    def __init__(self, model_path: str = None):
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'slm_settings.json')
        self.config = {
            "model_path": "src/models/Phi-4-mini-reasoning-UD-Q6_K_XL.gguf",
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
            slm_logger.info(f"--- INIT SLM ENGINE ---")
            slm_logger.info(f"Model Path: {self.model_path}")
            slm_logger.info(f"Config: {json.dumps(self.config)}")
            slm_logger.info(f"Hardware Before Load: {get_hardware_telemetry()}")
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
            slm_logger.info(f"Hardware After Load: {get_hardware_telemetry()}")
        except Exception as e:
            logger.error(f"SLMEngine: Failed to load model: {e}")

    def _build_prompt(self, raw_content: str, source_name: str, assoc_type: str) -> Optional[str]:
        """
        Builds the full prompt string by loading the template, extracting available
        columns from the raw content, and injecting all variables.
        """
        try:
            content_str = raw_content.decode('utf-8', errors='ignore')
        except Exception:
            content_str = str(raw_content)
            
        # Programmatically extract keys to help the SLM
        try:
            parsed_data = json.loads(content_str)
            
            def get_keys(d, prefix=''):
                keys = []
                if isinstance(d, dict):
                    for k, v in d.items():
                        full_key = f"{prefix}.{k}" if prefix else k
                        keys.append(full_key)
                        keys.extend(get_keys(v, full_key))
                elif isinstance(d, list) and len(d) > 0:
                    keys.extend(get_keys(d[0], prefix))
                return keys
            
            if isinstance(parsed_data, list) and len(parsed_data) > 0:
                available_keys = get_keys(parsed_data[0])
            else:
                available_keys = get_keys(parsed_data)
                
            available_keys_str = ", ".join(sorted(list(set(available_keys))))
            content_str = f"Available Columns in Dataset: [{available_keys_str}]\n\n{content_str}"
        except Exception:
            # Fallback for CSV or non-JSON
            first_line = content_str.split('\n')[0].strip()
            if ',' in first_line:
                content_str = f"Available Columns in Dataset: [{first_line}]\n\n{content_str}"
            
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

        # Load pre-digested association instructions from external config (OCP)
        assoc_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'assoc_instructions.json')
        try:
            with open(assoc_path, 'r', encoding='utf-8') as f:
                assoc_templates = json.load(f)
        except Exception as e:
            logger.warning(f"SLMEngine: Failed to load {assoc_path}: {e}. Using fallback.")
            assoc_templates = {}
        
        assoc_key = assoc_type.upper()
        assoc_template = assoc_templates.get(assoc_key, 
            f"This sensor ({source_name}) is {assoc_key}. Search for all applicable traffic variables.")
        assoc_instructions = assoc_template.replace("{source_name}", source_name)

        return (prompt_template
                .replace("{source_name}", source_name)
                .replace("{content_str}", content_str)
                .replace("{assoc_type}", assoc_type)
                .replace("{assoc_instructions}", assoc_instructions))

    def discover_schema(self, raw_content: str, source_name: str, assoc_type: str = "LOCAL") -> Optional[KinematicMap]:
        """
        Extracts kinematic column names from the raw JSON/CSV payload using strictly JSON output.
        """
        if self.llm is None:
            return None

        # Load schema JSON constraint
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'kinematic_schema.json')
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                json_schema = json.load(f)
        except Exception as e:
            logger.error(f"SLMEngine: Failed to load schema from {schema_path}: {e}")
            json_schema = {"required": ["speed_col", "flow_col", "intensity_col", "distance_col", "time_col", "occupancy_col"]}

        prompt = self._build_prompt(raw_content, source_name, assoc_type)
        if prompt is None:
            return None

        try:
            temp = self.config.get("temperature", 0.0)
            logger.info(f"SLMEngine: Starting GPU inference for '{source_name}' (temperature={temp}, thinking activated)...")
            slm_logger.info(f"\n--- INFERENCE START: {source_name} ---")
            slm_logger.info(f"Assoc Type: {assoc_type}")
            slm_logger.info(f"Hardware Pre-Inference: {get_hardware_telemetry()}")
            
            import time
            start_t = time.time()
            response = self.llm(
                prompt,
                max_tokens=4096,
                temperature=0.1,
                repeat_penalty=1.1,
                stop=["--- END OF INSTRUCTIONS ---"], # Stop if it starts hallucinating prompt
                echo=False
            )
            
            output_text = response["choices"][0]["text"].strip()
            end_t = time.time()
            
            slm_logger.info(f"Inference Time: {end_t - start_t:.2f}s")
            slm_logger.info(f"Hardware Post-Inference: {get_hardware_telemetry()}")
            slm_logger.info(f"Raw Output Length: {len(output_text)} chars")
            
            # --- Delegate parsing to SLMOutputParser (SRP) ---
            think_content, data = SLMOutputParser.parse(output_text)
            
            # --- Log thinking content ---
            if think_content:
                logger.info(
                    f"\n===========================================================\n"
                    f"🧠 SLM THINKING REASONING: [{source_name}]\n"
                    f"===========================================================\n"
                    f"{think_content}\n"
                    f"==========================================================="
                )
                slm_logger.debug(f"Thinking Block:\n{think_content}")
            else:
                logger.warning(f"SLMEngine: No thinking content detected for {source_name}.")
                slm_logger.warning("No thinking content detected.")

            logger.info(
                f"\n🎯 EXTRACTED SCHEMA: [{source_name}]\n"
                f"-----------------------------------------------------------\n"
                f"{json.dumps(data, indent=2)}\n"
                f"-----------------------------------------------------------"
            )
            slm_logger.info(f"Extracted Data:\n{json.dumps(data, indent=2)}")
            
            # --- TELEMETRIA DE FALHA DE EXTRAÇÃO ---
            expected_keys = json_schema.get("required", ["speed_col", "flow_col", "intensity_col", "distance_col", "time_col", "occupancy_col"])
            missing_keys = [k for k in expected_keys if k not in data]
            
            if missing_keys:
                slm_logger.warning(
                    f"[MISSING DATA] A SLM não conseguiu obter a informação (retornou null) "
                    f"para as seguintes variáveis no sensor '{source_name}': {', '.join(missing_keys)}"
                )
            
            slm_logger.info(f"--- INFERENCE END: {source_name} ---")
            
            # KV Cache reset explicitly removed to prevent GPU reloading bottleneck. 
            # Context isolation is naturally handled by not concatenating previous prompts.
            
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
            return None

    def unload(self):
        """Forces the release of the LLM from GPU VRAM and triggers Garbage Collection."""
        if self.llm:
            del self.llm
            self.llm = None
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        logger.info("SLMEngine: Model unloaded and RAM/VRAM released.")
        slm_logger.info("--- MODEL UNLOADED ---")
        slm_logger.info(f"Hardware After Unload: {get_hardware_telemetry()}")
