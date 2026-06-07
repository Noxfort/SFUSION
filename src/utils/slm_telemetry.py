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

# File: src/utils/slm_telemetry.py
# Author: Gabriel Moraes
# Date: 2026-06-07

"""SLM Telemetry - Hardware and execution metrics for SLM engine"""

import os
import logging
from src.utils.i18n import backend_i18n
import subprocess

def setup_slm_logger():
    slm_logger = logging.getLogger("SLM_TELEMETRY")
    slm_logger.setLevel(logging.DEBUG)
    if not slm_logger.handlers:
        fh = logging.FileHandler("Sfusion_slm.log", encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [SLM_TELEMETRY] %(message)s')
        fh.setFormatter(formatter)
        slm_logger.addHandler(fh)
        slm_logger.propagate = False # Prevent spamming main console
    return slm_logger

slm_logger = setup_slm_logger()

def get_hardware_telemetry():
    telemetry = []
    
    # 1. CPU RAM Usage
    try:
        import psutil
        process = psutil.Process(os.getpid())
        ram_usage = process.memory_info().rss / (1024 * 1024)
        telemetry.append(backend_i18n.t("telemetry.ram_cpu", ram=ram_usage))
    except ImportError:
        # Fallback to standard library if psutil is not installed
        import resource
        # ru_maxrss is in kilobytes on Linux
        ram_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        telemetry.append(backend_i18n.t("telemetry.ram_cpu_peak", ram=ram_usage))

    # 2. Real GPU VRAM Usage (using nvidia-smi as fallback for llama.cpp allocations)
    # We use nvidia-smi to get accurate VRAM since llama.cpp bypasses PyTorch
    try:
        # Get total memory used by the current process on the GPU
        pid = str(os.getpid())
        smi_out = subprocess.check_output(
            ['nvidia-smi', '--query-compute-apps=pid,used_memory', '--format=csv,noheader,nounits'],
            text=True
        )
        process_vram_mb = 0.0
        for line in smi_out.strip().split('\n'):
            if line:
                p, mem = line.split(',')
                if p.strip() == pid:
                    process_vram_mb += float(mem.strip())
        
        if process_vram_mb > 0:
            telemetry.append(backend_i18n.t("telemetry.vram_smi", vram=process_vram_mb))
        else:
            # If our PID isn't listed, maybe get total VRAM used generally
            smi_total = subprocess.check_output(
                ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                text=True
            ).strip().split('\n')[0]
            telemetry.append(backend_i18n.t("telemetry.vram_total", vram=float(smi_total)))
            
    except Exception:
        # Fallback to PyTorch if nvidia-smi fails
        try:
            import torch
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / (1024 * 1024)
                telemetry.append(backend_i18n.t("telemetry.vram_torch", vram=allocated))
        except ImportError:
            pass

    return " | ".join(telemetry) if telemetry else backend_i18n.t("telemetry.unavailable")
