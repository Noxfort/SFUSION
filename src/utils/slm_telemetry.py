import os
import logging
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
        telemetry.append(f"RAM (CPU): {ram_usage:.2f} MB")
    except ImportError:
        # Fallback to standard library if psutil is not installed
        import resource
        # ru_maxrss is in kilobytes on Linux
        ram_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        telemetry.append(f"RAM (CPU Peak): {ram_usage:.2f} MB")

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
            telemetry.append(f"VRAM (NVIDIA-SMI): {process_vram_mb:.2f} MB")
        else:
            # If our PID isn't listed, maybe get total VRAM used generally
            smi_total = subprocess.check_output(
                ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                text=True
            ).strip().split('\n')[0]
            telemetry.append(f"VRAM (Total Used): {float(smi_total):.2f} MB")
            
    except Exception:
        # Fallback to PyTorch if nvidia-smi fails
        try:
            import torch
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / (1024 * 1024)
                telemetry.append(f"VRAM (Torch Alloc): {allocated:.2f} MB")
        except ImportError:
            pass

    return " | ".join(telemetry) if telemetry else "Hardware telemetry unavailable"
