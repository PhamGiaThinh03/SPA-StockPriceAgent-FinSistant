import torch
import sys
import os
import importlib.util
from transformers import T5ForConditionalGeneration, T5Tokenizer
from pathlib import Path

 # Explicitly import Config to avoid conflicts
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_file = os.path.join(parent_dir, 'config.py')
spec = importlib.util.spec_from_file_location("summarization_config", config_file)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
Config = config_module.Config

 # Import logger using absolute import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger
from typing import List
from tqdm import tqdm

 # Import Map-Reduce Summarizer
from .map_reduce_summarizer import MapReduceSummarizer

class NewsSummarizer:
    """Enhanced summarizer with Map-Reduce capability for long texts"""
    
    def __init__(self, use_map_reduce=True):
        self.device = torch.device(Config.DEVICE)
        self.use_map_reduce = use_map_reduce
        
        self._validate_model_path()
        self._load_model()
        
    # Initialize Map-Reduce summarizer if enabled
        if self.use_map_reduce:
            try:
                self.map_reduce_summarizer = MapReduceSummarizer()
                logger.info("Map-Reduce Summarizer initialized")
            except Exception as e:
                logger.warning(f"Map-Reduce initialization failed: {e}")
                logger.warning("Falling back to standard summarization")
                self.use_map_reduce = False
                
        self._warmup_model()
    
    def get_text_length_stats(self, text: str) -> dict:
        """Analyze text length to determine the best summarization approach"""
        token_count = len(self.tokenizer.encode("summarize: " + text, add_special_tokens=False))
        
        stats = {
            "char_count": len(text),
            "token_count": token_count,
            "exceeds_limit": token_count > Config.MAX_INPUT_LENGTH,
            "recommended_approach": "map_reduce" if token_count > Config.MAX_INPUT_LENGTH else "standard",
            "max_input_length": Config.MAX_INPUT_LENGTH
        }
        
        return stats
    
    def _validate_model_path(self):
        """Verify model files exist"""
        self.model_path = Path(Config.MODEL_PATH)
        required_files = ['config.json', 'model.safetensors', 
                         'tokenizer_config.json', 'spiece.model']
        
        missing = [f for f in required_files if not (self.model_path / f).exists()]
        if missing:
            raise FileNotFoundError(f"Missing model files: {missing}")

    def summarize_batch(self, texts: List[str]) -> List[str]:
        """Optimized batch processing with fallback"""
        if not texts:
            return []
            
        try:
            inputs = self.tokenizer(
                ["summarize: " + t for t in texts],
                max_length=Config.MAX_INPUT_LENGTH,
                truncation=True,
                padding="max_length",
                return_tensors="pt"
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **Config.get_generation_config()
                )
            
            return [self.tokenizer.decode(o, skip_special_tokens=True).strip() 
                   for o in outputs]
            
        except Exception as e:
            logger.warning(f"Batch failed: {str(e)}")
            return [self.summarize(text) for text in texts]

    def _load_model(self):
        """Safely load tokenizer and model"""
        try:
            logger.info("Loading tokenizer...")
            self.tokenizer = T5Tokenizer.from_pretrained(
                str(self.model_path),
                legacy=False,
                local_files_only=True
            )
            
            logger.info("Loading model weights...")
            self.model = T5ForConditionalGeneration.from_pretrained(
                str(self.model_path),
                local_files_only=True
            ).to(self.device)
            
            self.model.eval()
            logger.info(f"Model loaded on {self.device}")
            
        except Exception as e:
            logger.error("Model loading failed")
            logger.error(f"Error details: {str(e)}")
            raise RuntimeError("Failed to initialize summarizer") from e

    def _warmup_model(self):
        """Initial inference to trigger lazy loading"""
        try:
            logger.info("Warming up model...")
            test_text = "This is a warmup run. " * 10
            self.summarize(test_text)
            logger.info("Model ready")
        except Exception as e:
            logger.warning(f"Warmup failed (non-critical): {str(e)}")

    def summarize(self, text: str) -> str:
        """
        Generate summary for a single article with automatic approach selection
        
        Args:
            text: Input text to summarize
        Returns:
            str: Generated summary
        """
        if not text.strip():
            raise ValueError("Input text cannot be empty")
        
        # Analyze text length
        stats = self.get_text_length_stats(text)
        
        # Log analysis
        logger.info(f"Text analysis - Chars: {stats['char_count']}, "
                   f"Tokens: {stats['token_count']}, "
                   f"Exceeds limit: {stats['exceeds_limit']}")
        
        # Choose summarization approach
        if stats['exceeds_limit'] and self.use_map_reduce:
            logger.info("Using Map-Reduce summarization for long text")
            try:
                return self.map_reduce_summarizer.summarize(text)
            except Exception as e:
                logger.warning(f"Map-Reduce failed, falling back to truncation: {e}")
                return self._standard_summarize(text)
        else:
            if stats['exceeds_limit']:
                logger.warning(f"Text exceeds token limit ({stats['token_count']} > {stats['max_input_length']}), truncating...")
            logger.info("Using standard summarization")
            return self._standard_summarize(text)
    
    def _standard_summarize(self, text: str) -> str:
        """Standard summarization with truncation"""
        try:
            input_text = "summarize: " + text.strip()
            
            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                max_length=Config.MAX_INPUT_LENGTH,
                truncation=True,
                padding="max_length"
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **Config.get_generation_config()
                )
            
            return self._clean_output(outputs[0])
            
        except torch.cuda.OutOfMemoryError:
            logger.error("CUDA out of memory - reduce input length or batch size")
            raise
        except Exception as e:
            logger.error(f"Standard summarization failed for text: {text[:50]}...")
            logger.error(f"Error: {str(e)}")
            raise RuntimeError("Summarization failed") from e

    def summarize_batch(self, texts: List[str]) -> List[str]:
        """Enhanced batch processing with Map-Reduce support"""
        if not texts:
            return []
        
        # Analyze all texts to determine processing strategy
        long_texts = []
        short_texts = []
        long_indices = []
        short_indices = []
        
        for i, text in enumerate(texts):
            stats = self.get_text_length_stats(text)
            if stats['exceeds_limit'] and self.use_map_reduce:
                long_texts.append(text)
                long_indices.append(i)
            else:
                short_texts.append(text)
                short_indices.append(i)
        
        logger.info(f"Batch analysis: {len(long_texts)} long texts, {len(short_texts)} short texts")
        
        # Initialize results array
        results = [""] * len(texts)
        
        # Process long texts individually with Map-Reduce
        if long_texts:
            logger.info("Processing long texts with Map-Reduce...")
            for i, text in enumerate(long_texts):
                try:
                    result = self.map_reduce_summarizer.summarize(text)
                    results[long_indices[i]] = result
                    logger.info(f"Completed long text {i+1}/{len(long_texts)}")
                except Exception as e:
                    logger.warning(f"Map-Reduce failed for text {i+1}, using standard: {e}")
                    results[long_indices[i]] = self._standard_summarize(text)
        
        # Process short texts in batch
        if short_texts:
            logger.info("Processing short texts in batch...")
            try:
                short_results = self._batch_summarize_standard(short_texts)
                for i, result in enumerate(short_results):
                    results[short_indices[i]] = result
            except Exception as e:
                logger.warning(f"Batch processing failed, falling back to sequential: {e}")
                for i, text in enumerate(short_texts):
                    results[short_indices[i]] = self._standard_summarize(text)
        
        return results
    
    def _batch_summarize_standard(self, texts: List[str]) -> List[str]:
        """Standard batch processing for short texts"""
        # Automatic fallback to sequential on CPU or small batches
        if Config.DEVICE == "cpu" or len(texts) <= 2:
            return [self._standard_summarize(text) for text in texts]
        try:
            input_texts = ["summarize: " + t.strip() for t in texts]
            inputs = self.tokenizer(
                input_texts,
                return_tensors="pt",
                max_length=Config.MAX_INPUT_LENGTH,
                truncation=True,
                padding="max_length"
            ).to(self.device)
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **Config.get_generation_config()
                )
            return [self._clean_output(output) for output in outputs]
        except RuntimeError as e:
            logger.warning(f"Standard batch failed: {str(e)}")
            return [self._standard_summarize(text) for text in texts]

    def _clean_output(self, output_tensor: torch.Tensor) -> str:
        """Clean and format model output"""
        return self.tokenizer.decode(
            output_tensor,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True
        ).strip()
    
    def get_configuration_info(self) -> dict:
        """Get comprehensive configuration information"""
        config_info = {
            "device": str(self.device),
            "max_input_length": Config.MAX_INPUT_LENGTH,
            "max_target_length": Config.MAX_TARGET_LENGTH,
            "batch_size": Config.BATCH_SIZE,
            "model_path": str(self.model_path),
            "map_reduce_enabled": self.use_map_reduce
        }
        
        if self.use_map_reduce and hasattr(self, 'map_reduce_summarizer'):
            config_info["map_reduce_stats"] = self.map_reduce_summarizer.get_statistics()
        
        return config_info
    
    def toggle_map_reduce(self, enable: bool = None) -> bool:
        """Toggle Map-Reduce functionality on/off"""
        if enable is None:
            self.use_map_reduce = not self.use_map_reduce
        else:
            self.use_map_reduce = enable
        
        if self.use_map_reduce and not hasattr(self, 'map_reduce_summarizer'):
            try:
                self.map_reduce_summarizer = MapReduceSummarizer()
                logger.info("Map-Reduce Summarizer enabled")
            except Exception as e:
                logger.error(f"Failed to enable Map-Reduce: {e}")
                self.use_map_reduce = False
        logger.info(f"Map-Reduce summarization: {'ENABLED' if self.use_map_reduce else 'DISABLED'}")
        return self.use_map_reduce