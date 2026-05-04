import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import logging
import time
import os
from typing import Tuple, List
import numpy as np

logger = logging.getLogger(__name__)


class TrOCREngine:
    """
    Singleton wrapper for TrOCR. Loads model once on startup,
    caches to disk at ~/.cache/trocr/ to avoid re-downloading.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TrOCREngine, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._load_model()
            TrOCREngine._initialized = True
    
    def _load_model(self):
        """Load TrOCR processor and model, move to GPU if available"""
        start_time = time.time()
        
        try:
            # Set cache directory
            cache_dir = os.path.expanduser("~/.cache/trocr/")
            os.makedirs(cache_dir, exist_ok=True)
            
            model_name = os.getenv("TROCR_MODEL", "microsoft/trocr-large-handwritten")
            
            logger.info(f"Loading TrOCR model: {model_name}")
            
            # Load processor and model
            self.processor = TrOCRProcessor.from_pretrained(
                model_name, 
                cache_dir=cache_dir
            )
            
            self.model = VisionEncoderDecoderModel.from_pretrained(
                model_name,
                cache_dir=cache_dir
            )
            
            # Move to GPU if available
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = self.model.to(self.device)
            
            # Set to evaluation mode
            self.model.eval()
            
            load_time = time.time() - start_time
            logger.info(f"TrOCR model loaded in {load_time:.2f}s on {self.device}")
            
            # Test inference to warm up
            test_image = Image.new('RGB', (224, 224), color='white')
            self._warmup(test_image)
            
        except Exception as e:
            logger.error(f"Failed to load TrOCR model: {e}")
            raise
    
    def _warmup(self, test_image: Image.Image):
        """Warm up the model with a test inference"""
        try:
            with torch.no_grad():
                pixel_values = self.processor(test_image, return_tensors="pt").pixel_values
                pixel_values = pixel_values.to(self.device)
                generated_ids = self.model.generate(pixel_values, max_length=50)
                self.processor.batch_decode(generated_ids, skip_special_tokens=True)
            logger.info("Model warmup completed")
        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")
    
    def extract_text(self, image: Image.Image) -> Tuple[str, float]:
        """
        Extract text from image using TrOCR.
        
        Returns:
            Tuple of (raw_text, confidence_score)
            Confidence = mean of token probabilities from model output
        """
        start_time = time.time()
        
        try:
            # Preprocess image
            pixel_values = self.processor(image, return_tensors="pt").pixel_values
            pixel_values = pixel_values.to(self.device)
            
            # Generate text with scores
            with torch.no_grad():
                outputs = self.model.generate(
                    pixel_values,
                    max_length=512,
                    num_beams=4,
                    early_stopping=True,
                    return_dict_in_generate=True,
                    output_scores=True
                )
            
            # Decode generated text
            generated_text = self.processor.batch_decode(
                outputs.sequences, 
                skip_special_tokens=True
            )[0]
            
            # Calculate confidence from scores
            confidence = self._calculate_confidence(outputs)
            
            inference_time = time.time() - start_time
            logger.info(f"OCR completed in {inference_time:.2f}s, confidence: {confidence:.3f}")
            
            return generated_text.strip(), confidence
            
        except torch.cuda.OutOfMemoryError:
            logger.warning("GPU OOM, falling back to CPU")
            return self._extract_text_cpu_fallback(image)
        
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return "", 0.0
    
    def _extract_text_cpu_fallback(self, image: Image.Image) -> Tuple[str, float]:
        """Fallback to CPU inference on GPU OOM"""
        try:
            # Move model to CPU
            self.model = self.model.to("cpu")
            self.device = "cpu"
            
            # Retry extraction
            return self.extract_text(image)
            
        except Exception as e:
            logger.error(f"CPU fallback failed: {e}")
            return "", 0.0
    
    def _calculate_confidence(self, outputs) -> float:
        """Calculate confidence score from model outputs"""
        try:
            if hasattr(outputs, 'scores') and outputs.scores:
                # Convert scores to probabilities and calculate mean
                scores = torch.stack(outputs.scores, dim=1)  # [batch, seq_len, vocab_size]
                probs = torch.softmax(scores, dim=-1)
                
                # Get probabilities of selected tokens
                selected_tokens = outputs.sequences[:, 1:]  # Skip BOS token
                
                # Calculate mean probability of selected tokens
                token_probs = []
                for i, token_id in enumerate(selected_tokens[0]):
                    if i < len(outputs.scores):
                        prob = probs[0, i, token_id].item()
                        token_probs.append(prob)
                
                if token_probs:
                    confidence = np.mean(token_probs)
                    return min(max(confidence, 0.0), 1.0)  # Clamp to [0, 1]
            
            # Fallback confidence based on text length and content
            return 0.5
            
        except Exception as e:
            logger.warning(f"Confidence calculation failed: {e}")
            return 0.5
    
    def extract_text_batch(self, images: List[Image.Image]) -> List[Tuple[str, float]]:
        """
        Batch inference for efficiency.
        
        Args:
            images: List of PIL Images
            
        Returns:
            List of (text, confidence) tuples
        """
        if not images:
            return []
        
        start_time = time.time()
        results = []
        
        try:
            # Process images in batches of 4 to manage memory
            batch_size = 4
            
            for i in range(0, len(images), batch_size):
                batch = images[i:i + batch_size]
                batch_results = self._process_batch(batch)
                results.extend(batch_results)
            
            total_time = time.time() - start_time
            logger.info(f"Batch OCR completed: {len(images)} images in {total_time:.2f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"Batch OCR failed: {e}")
            # Fallback to individual processing
            return [self.extract_text(img) for img in images]
    
    def _process_batch(self, images: List[Image.Image]) -> List[Tuple[str, float]]:
        """Process a batch of images"""
        try:
            # Preprocess batch
            pixel_values = self.processor(images, return_tensors="pt").pixel_values
            pixel_values = pixel_values.to(self.device)
            
            # Generate text for batch
            with torch.no_grad():
                outputs = self.model.generate(
                    pixel_values,
                    max_length=512,
                    num_beams=4,
                    early_stopping=True,
                    return_dict_in_generate=True,
                    output_scores=True
                )
            
            # Decode all texts
            generated_texts = self.processor.batch_decode(
                outputs.sequences, 
                skip_special_tokens=True
            )
            
            # Calculate confidence for each
            results = []
            for i, text in enumerate(generated_texts):
                confidence = self._calculate_batch_confidence(outputs, i)
                results.append((text.strip(), confidence))
            
            return results
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            # Fallback to individual processing
            return [self.extract_text(img) for img in images]
    
    def _calculate_batch_confidence(self, outputs, batch_idx: int) -> float:
        """Calculate confidence for a specific item in batch"""
        try:
            if hasattr(outputs, 'scores') and outputs.scores:
                # Similar to single confidence calculation but for specific batch item
                scores = torch.stack(outputs.scores, dim=1)
                probs = torch.softmax(scores, dim=-1)
                
                selected_tokens = outputs.sequences[batch_idx, 1:]  # Skip BOS token
                
                token_probs = []
                for i, token_id in enumerate(selected_tokens):
                    if i < len(outputs.scores):
                        prob = probs[batch_idx, i, token_id].item()
                        token_probs.append(prob)
                
                if token_probs:
                    confidence = np.mean(token_probs)
                    return min(max(confidence, 0.0), 1.0)
            
            return 0.5
            
        except Exception as e:
            logger.warning(f"Batch confidence calculation failed: {e}")
            return 0.5


# Global instance
ocr_engine = TrOCREngine()