import torch
from transformers import AutoModelForCausalLM, AutoProcessor
import logging
import gc
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelLoader:
    _instance = None

    def __new__(cls, config):
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
            cls._instance.config = config
            cls._instance.model = None
            cls._instance.processor = None
        return cls._instance

    def load(self):
        if self.model is not None:
            logger.info("Model already loaded.")
            return

        logger.info(f"Loading model from {self.config['model']['path']}...")
        try:
            from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, AutoModelForCausalLM
            
            # Try specific Qwen2.5-VL if available (for future compat)
            ModelClass = Qwen2_5_VLForConditionalGeneration
        except ImportError:
            # Fallback to Qwen2VL or AutoModel
            from transformers import Qwen2VLForConditionalGeneration, AutoProcessor, AutoModelForCausalLM
            if "Qwen2_5" in self.config['model']['path'] or "Dolphin" in self.config['model']['path']:
                 # If model is Qwen2.5 based but library doesn't have class, try AutoModel or Qwen2VL (sometimes compatible)
                 # Note: Qwen2.5 VL usually needs latest transformers. If 4.49+ not available, Qwen2VL might work if arch matches.
                 # Let's try AutoModel first as it's safer if config.json is correct.
                 ModelClass = AutoModelForCausalLM 
            else:
                 ModelClass = Qwen2VLForConditionalGeneration

        try:
            # Load MODEL first
            self.model = ModelClass.from_pretrained(
                self.config['model']['path'],
                torch_dtype=getattr(torch, self.config['model']['torch_dtype']),
                device_map=self.config['model']['device_map'],
                trust_remote_code=self.config['model']['trust_remote_code'],
            )
            logger.info(f"Model loaded successfully using {ModelClass.__name__}.")
            
            # Load PROCESSOR second
            self.processor = AutoProcessor.from_pretrained(
                self.config['model']['path'], 
                trust_remote_code=self.config['model']['trust_remote_code']
            )
            logger.info("Processor loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise e

    def unload(self):
        if self.model is None:
            return

        logger.info("Unloading model...")
        del self.model
        del self.processor
        self.model = None
        self.processor = None
        
        # Force garbage collection and empty cache
        gc.collect()
        if torch.backends.mps.is_available():
             torch.mps.empty_cache()
        elif torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        logger.info("Model unloaded.")

    def is_loaded(self):
        return self.model is not None

    def get_model(self):
        if not self.is_loaded():
            self.load()
        return self.model

    def get_processor(self):
        if not self.is_loaded():
            self.load()
        return self.processor

    def get_vram_usage(self):
        # Approximate VRAM usage check
        if torch.backends.mps.is_available():
            # MPS specific memory check if available (limited in PyTorch)
            return torch.mps.current_allocated_memory() / (1024 * 1024)
        elif torch.cuda.is_available():
            return torch.cuda.memory_allocated() / (1024 * 1024)
        return 0
