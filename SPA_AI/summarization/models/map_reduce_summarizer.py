import torch
import sys
import os
import importlib.util
from transformers import T5ForConditionalGeneration, T5Tokenizer
from pathlib import Path
from typing import List, Dict, Any
import math

# Import Config và logger
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_file = os.path.join(parent_dir, 'config.py')
spec = importlib.util.spec_from_file_location("summarization_config", config_file)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
Config = config_module.Config

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import logger


class MapReduceSummarizer:
    """
    Map-Reduce Summarization Implementation
    Xử lý văn bản dài bằng cách phân tầng (hierarchical summarization)
    
    Pipeline:
    1. Đo độ dài văn bản
    2. MAP: Cắt thành chunks với overlap, tóm tắt từng chunk
    3. REDUCE: Ghép và tóm tắt các partial summaries
    4. FINAL: Tóm tắt cuối cùng để tăng tính mạch lạc
    """
    
    def __init__(self):
        self.device = torch.device(Config.DEVICE)
        self._validate_model_path()
        self._load_model()
        
        # Map-Reduce Configuration
        self.max_src_len = Config.MAX_INPUT_LENGTH  # 1024
        self.prefix_tokens = 20  # "summarize: " + margin
        self.available_src = self.max_src_len - self.prefix_tokens  # 1004
        
        # Chunking parameters
        self.chunk_overlap = 128  # Overlap giữa các chunk để tránh đứt mạch ý
        self.min_chunk_size = 256  # Minimum chunk size
        
        # Generation configurations for different phases
        self.map_config = {
            "max_length": 128,  # Ngắn cho MAP phase
            "min_length": 30,
            "num_beams": 2,
            "repetition_penalty": 1.1,
            "length_penalty": 1.0,
            "early_stopping": True,
            "no_repeat_ngram_size": 2
        }
        
        self.reduce_config = {
            "max_length": 200,  # Dài hơn cho REDUCE phase
            "min_length": 50,
            "num_beams": 3,
            "repetition_penalty": 1.2,
            "length_penalty": 1.0,
            "early_stopping": True,
            "no_repeat_ngram_size": 3
        }
        
        self.final_config = {
            "max_length": Config.MAX_TARGET_LENGTH,  # 256
            "min_length": 80,
            "num_beams": 4,
            "repetition_penalty": 1.2,
            "length_penalty": 1.1,
            "early_stopping": True,
            "no_repeat_ngram_size": 3
        }
        
        # Control parameters
        self.max_reduce_rounds = 3  # Tối đa 3 vòng reduce
        
        logger.info("Map-Reduce Summarizer initialized")
        logger.info(f"Max input length: {self.max_src_len}")
        logger.info(f"Available source length: {self.available_src}")
        logger.info(f"Chunk overlap: {self.chunk_overlap}")
    
    def _validate_model_path(self):
        """Verify model files exist"""
        self.model_path = Path(Config.MODEL_PATH)
        required_files = ['config.json', 'model.safetensors', 
                         'tokenizer_config.json', 'spiece.model']
        
        missing = [f for f in required_files if not (self.model_path / f).exists()]
        if missing:
            raise FileNotFoundError(f"Missing model files: {missing}")
    
    def _load_model(self):
        """Load tokenizer and model"""
        try:
            logger.info("Loading Map-Reduce tokenizer...")
            self.tokenizer = T5Tokenizer.from_pretrained(
                str(self.model_path),
                legacy=False,
                local_files_only=True
            )
            
            logger.info("Loading Map-Reduce model...")
            self.model = T5ForConditionalGeneration.from_pretrained(
                str(self.model_path),
                local_files_only=True
            ).to(self.device)
            
            self.model.eval()
            logger.info(f"Map-Reduce model loaded on {self.device}")
            
        except Exception as e:
            logger.error("Map-Reduce model loading failed")
            raise RuntimeError("Failed to initialize Map-Reduce summarizer") from e
    
    def count_tokens(self, text: str) -> int:
        """Đếm số token của văn bản"""
        return len(self.tokenizer.encode(text, add_special_tokens=False))
    
    def summarize(self, text: str) -> str:
        """
        Main summarization function với Map-Reduce
        
        Args:
            text: Văn bản cần tóm tắt
            
        Returns:
            str: Bản tóm tắt cuối cùng
        """
        if not text.strip():
            raise ValueError("Input text cannot be empty")
        
        # 1. Đo độ dài
        input_text = "summarize: " + text.strip()
        total_tokens = self.count_tokens(input_text)
        
        logger.info(f"Input text tokens: {total_tokens}")
        
        # 2. Nếu ngắn hơn max_src_len → tóm tắt 1-pass
        if total_tokens <= self.max_src_len:
            logger.info("Text fits in context, using single-pass summarization")
            return self._single_pass_summarize(text)
        
        # 3. Map-Reduce pipeline cho văn bản dài
        logger.info("Text too long, using Map-Reduce pipeline")
        return self._map_reduce_summarize(text)
    
    def _single_pass_summarize(self, text: str) -> str:
        """Tóm tắt 1-pass cho văn bản ngắn"""
        try:
            input_text = "summarize: " + text.strip()
            
            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                max_length=self.max_src_len,
                truncation=True,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **self.final_config
                )
            
            return self._clean_output(outputs[0])
            
        except Exception as e:
            logger.error(f"Single-pass summarization failed: {str(e)}")
            raise
    
    def _map_reduce_summarize(self, text: str) -> str:
        """Map-Reduce pipeline cho văn bản dài"""
        try:
            # MAP Phase: Cắt và tóm tắt từng chunk
            chunks = self._create_chunks(text)
            logger.info(f"Created {len(chunks)} chunks for MAP phase")
            
            partial_summaries = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                summary = self._map_summarize(chunk)
                partial_summaries.append(summary)
            
            # REDUCE Phase: Ghép và giảm dần
            current = " ".join(partial_summaries)
            reduce_round = 0
            
            while reduce_round < self.max_reduce_rounds:
                current_tokens = self.count_tokens("summarize: " + current)
                logger.info(f"Reduce round {reduce_round + 1}: {current_tokens} tokens")
                
                if current_tokens <= self.available_src:
                    break
                
                # Cần reduce thêm
                current = self._reduce_summarize(current)
                reduce_round += 1
            
            # FINAL Phase: Tóm tắt cuối cùng
            logger.info("Final summarization phase")
            return self._final_summarize(current)
            
        except Exception as e:
            logger.error(f"Map-Reduce summarization failed: {str(e)}")
            raise
    
    def _create_chunks(self, text: str) -> List[str]:
        """
        Cắt văn bản thành các chunk với overlap
        
        Args:
            text: Văn bản gốc
            
        Returns:
            List[str]: Danh sách các chunk
        """
        # Tokenize toàn bộ văn bản
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        total_tokens = len(tokens)
        
        if total_tokens <= self.available_src:
            return [text]
        
        chunks = []
        chunk_size = self.available_src - self.chunk_overlap
        
        start = 0
        while start < total_tokens:
            # Xác định end position
            end = min(start + chunk_size, total_tokens)
            
            # Lấy chunk tokens
            chunk_tokens = tokens[start:end]
            
            # Decode chunk
            chunk_text = self.tokenizer.decode(chunk_tokens, skip_special_tokens=True)
            
            # Đảm bảo chunk không quá ngắn (trừ chunk cuối)
            if len(chunk_text.strip()) >= self.min_chunk_size or end >= total_tokens:
                chunks.append(chunk_text.strip())
            
            # Di chuyển start position với overlap
            if end >= total_tokens:
                break
            start = end - self.chunk_overlap
        
        return chunks
    
    def _map_summarize(self, chunk: str) -> str:
        """MAP phase: Tóm tắt một chunk"""
        try:
            input_text = "summarize: " + chunk
            
            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                max_length=self.max_src_len,
                truncation=True,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **self.map_config
                )
            
            return self._clean_output(outputs[0])
            
        except Exception as e:
            logger.error(f"MAP summarization failed for chunk: {str(e)}")
            # Fallback: trả về chunk gốc (truncated)
            return chunk[:500] + "..."
    
    def _reduce_summarize(self, text: str) -> str:
        """REDUCE phase: Tóm tắt các partial summaries"""
        try:
            input_text = "summarize: " + text
            
            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                max_length=self.max_src_len,
                truncation=True,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **self.reduce_config
                )
            
            return self._clean_output(outputs[0])
            
        except Exception as e:
            logger.error(f"REDUCE summarization failed: {str(e)}")
            # Fallback: truncate
            return text[:1000] + "..."
    
    def _final_summarize(self, text: str) -> str:
        """FINAL phase: Tóm tắt cuối cùng để tăng tính mạch lạc"""
        try:
            input_text = "summarize: " + text
            
            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                max_length=self.max_src_len,
                truncation=True,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **self.final_config
                )
            
            return self._clean_output(outputs[0])
            
        except Exception as e:
            logger.error(f"FINAL summarization failed: {str(e)}")
            # Fallback: return input as is (truncated)
            return text[:500] + "..."
    
    def _clean_output(self, output_tensor: torch.Tensor) -> str:
        """Clean and format model output"""
        return self.tokenizer.decode(
            output_tensor,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True
        ).strip()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Trả về thống kê về cấu hình Map-Reduce"""
        return {
            "max_input_length": self.max_src_len,
            "available_source_length": self.available_src,
            "chunk_overlap": self.chunk_overlap,
            "min_chunk_size": self.min_chunk_size,
            "max_reduce_rounds": self.max_reduce_rounds,
            "map_max_length": self.map_config["max_length"],
            "reduce_max_length": self.reduce_config["max_length"],
            "final_max_length": self.final_config["max_length"],
            "device": str(self.device)
        }
