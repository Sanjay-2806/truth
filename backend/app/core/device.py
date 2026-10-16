"""Hardware device manager for PyTorch / Hugging Face models in TruthGuard AI.

Detects Apple Silicon (MPS), CUDA, or CPU fallback.
"""

import os
import torch
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("truthguard.device")


def get_device() -> torch.device:
    """Resolves and returns the optimal torch.device based on hardware and configuration."""
    configured = settings.DEVICE.lower()

    if configured == "mps":
        if torch.backends.mps.is_available():
            return torch.device("mps")
        logger.warning("MPS configured but not available. Falling back to CPU.")
        return torch.device("cpu")

    if configured == "cuda":
        if torch.cuda.is_available():
            return torch.device("cuda")
        logger.warning("CUDA configured but not available. Falling back to CPU.")
        return torch.device("cpu")

    if configured == "cpu":
        return torch.device("cpu")

    # Auto detection: Priority is MPS on macOS, then CUDA, then CPU
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")


def get_device_info() -> dict:
    """Returns a dictionary of detailed hardware accelerator diagnostic information."""
    dev = get_device()
    info = {
        "selected_device": str(dev),
        "mps_available": torch.backends.mps.is_available(),
        "mps_built": torch.backends.mps.is_built(),
        "cuda_available": torch.cuda.is_available(),
        "pytorch_version": torch.__version__,
    }
    return info
