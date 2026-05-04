import asyncio
import logging
import time
import uuid
from typing import Dict, Any
from models import ExtractionResult, MedicineItem
from preprocess import preprocess_prescription_image, segment_into_lines
from ocr import ocr_engine
from extractor import LLMExtractor
from validator import validate_all_medicines
from database import db_manager, calculate_image_hash
import os
import numpy as np

logger = logging.getLogger(__name__)


class PrescriptionPipeline:
    """Main orchestration pipeline for prescription processing"""
    
    def __init__(self):
        self.llm_extractor = LLMExtractor()
        self.model_name = f"TrOCR-large + {os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')}"
    
    async def run_pipeline(self, image_bytes: bytes) -> ExtractionResult:
        """
        Orchestrate the full pipeline. Time each stage. Log to processing_log table.
        
        Stages:
        1. preprocess_prescription_image(image_bytes)
           → processed_image, preprocess_meta
        
        2. ocr_engine.extract_text(processed_image)
           → ocr_text, ocr_confidence
           If ocr_confidence < 0.3: add "Low OCR confidence" to extraction_failures
        
        3. llm_extractor.extract(ocr_text)
           → extraction_dict
        
        4. validate_all_medicines(extraction_dict["medicines"])
           → validated_medicines (with fda_verified + india_db_verified added)
        
        5. Build ExtractionResult from all outputs
           Set model_used = "TrOCR-large + {GROQ_MODEL}"
        
        6. Save to DB
        
        7. Return ExtractionResult
        
        On any stage failure: continue with partial results.
        Never raise — always return an ExtractionResult (even with failures logged).
        """
        
        start_time = time.time()
        prescription_id = str(uuid.uuid4())
        image_hash = calculate_image_hash(image_bytes)
        
        # Initialize result with defaults
        result_data = {
            "id": prescription_id,
            "patient_name": None,
            "date": None,
            "doctor_name": None,
            "doctor_reg_no": None,
            "medicines": [],
            "general_instructions": None,
            "followup_date": None,
            "ocr_raw": "",
            "ocr_confidence": 0.0,
            "extraction_failures": [],
            "processing_time_ms": 0,
            "model_used": self.model_name
        }
        
        logger.info(f"Starting pipeline for prescription {prescription_id}")
        
        # Stage 1: Preprocessing
        stage_start = time.time()
        try:
            processed_image, preprocess_meta = preprocess_prescription_image(image_bytes)
            stage_duration = int((time.time() - stage_start) * 1000)
            
            db_manager.log_processing_stage(
                prescription_id, "preprocess", stage_duration, True
            )
            
            logger.info(f"Preprocessing completed in {stage_duration}ms")
            
        except Exception as e:
            stage_duration = int((time.time() - stage_start) * 1000)
            error_msg = f"Preprocessing failed: {str(e)}"
            
            db_manager.log_processing_stage(
                prescription_id, "preprocess", stage_duration, False, error_msg
            )
            
            result_data["extraction_failures"].append(error_msg)
            logger.error(error_msg)
            
            # Create a fallback blank image
            from PIL import Image
            processed_image = Image.new('RGB', (800, 600), color='white')
        
        # Stage 2: Line Segmentation + OCR
        stage_start = time.time()
        try:
            # --- 2a. Segment preprocessed image into individual text lines ---
            line_images = segment_into_lines(processed_image)
            logger.info(f"Segmented into {len(line_images)} line(s) for OCR")

            # --- 2b. Run OCR over all lines ---
            # Prefer batch processing; fall back to per-line calls if the method
            # is unavailable (e.g. during development/testing).
            if hasattr(ocr_engine, "extract_text_batch"):
                line_results = ocr_engine.extract_text_batch(line_images)
                # Expected return type: List[Tuple[str, float]]
                # Each element is (line_text, confidence_score).
            else:
                # Graceful fallback: call extract_text once per line
                logger.warning(
                    "ocr_engine.extract_text_batch not found — "
                    "falling back to per-line extract_text calls"
                )
                line_results = [ocr_engine.extract_text(img) for img in line_images]

            # --- 2c. Assemble full text and compute mean confidence ---
            line_texts = []
            confidences = []
            for line_text, line_conf in line_results:
                stripped = line_text.strip()
                if stripped:                  # ignore blank lines from noise crops
                    line_texts.append(stripped)
                    confidences.append(line_conf)

            ocr_text = "\n".join(line_texts)
            ocr_confidence = float(np.mean(confidences)) if confidences else 0.0

            # Debug log so you can verify segmentation before blaming the LLM
            logger.debug(f"OCR raw text ({len(line_texts)} non-empty lines):\n{ocr_text}")

            stage_duration = int((time.time() - stage_start) * 1000)

            result_data["ocr_raw"] = ocr_text
            result_data["ocr_confidence"] = ocr_confidence

            if ocr_confidence < 0.15:
                result_data["extraction_failures"].append("Low OCR confidence")
                logger.warning(f"Low OCR confidence: {ocr_confidence:.3f}")

            db_manager.log_processing_stage(
                prescription_id, "ocr", stage_duration, True
            )

            logger.info(
                f"OCR completed in {stage_duration}ms — "
                f"{len(line_texts)} lines, confidence: {ocr_confidence:.3f}"
            )
            
        except Exception as e:
            stage_duration = int((time.time() - stage_start) * 1000)
            error_msg = f"OCR failed: {str(e)}"
            
            db_manager.log_processing_stage(
                prescription_id, "ocr", stage_duration, False, error_msg
            )
            
            result_data["extraction_failures"].append(error_msg)
            result_data["ocr_raw"] = ""
            result_data["ocr_confidence"] = 0.0
            logger.error(error_msg)
            
            ocr_text = ""
        
        # Stage 3: LLM Extraction
        stage_start = time.time()
        try:
            if ocr_text.strip():
                extraction_dict = self.llm_extractor.extract(ocr_text)
                
                # Validate the extraction result
                extraction_dict = self.llm_extractor.validate_extraction_result(extraction_dict)
                
                # Merge extracted data
                for key in ["patient_name", "date", "doctor_name", "doctor_reg_no", 
                           "general_instructions", "followup_date"]:
                    if key in extraction_dict:
                        result_data[key] = extraction_dict[key]
                
                # Handle medicines
                if "medicines" in extraction_dict and extraction_dict["medicines"]:
                    result_data["medicines"] = extraction_dict["medicines"]
                
                # Merge extraction failures
                if "extraction_failures" in extraction_dict:
                    result_data["extraction_failures"].extend(extraction_dict["extraction_failures"])
                
                stage_duration = int((time.time() - stage_start) * 1000)
                
                db_manager.log_processing_stage(
                    prescription_id, "extract", stage_duration, True
                )
                
                logger.info(f"LLM extraction completed in {stage_duration}ms")
                
            else:
                result_data["extraction_failures"].append("No OCR text to extract from")
                stage_duration = int((time.time() - stage_start) * 1000)
                
                db_manager.log_processing_stage(
                    prescription_id, "extract", stage_duration, False, "No OCR text"
                )
                
        except Exception as e:
            stage_duration = int((time.time() - stage_start) * 1000)
            error_msg = f"LLM extraction failed: {str(e)}"
            
            db_manager.log_processing_stage(
                prescription_id, "extract", stage_duration, False, error_msg
            )
            
            result_data["extraction_failures"].append(error_msg)
            logger.error(error_msg)
        
        # Stage 4: Medicine Validation
        stage_start = time.time()
        try:
            if result_data["medicines"]:
                validated_medicines = await validate_all_medicines(result_data["medicines"])
                result_data["medicines"] = validated_medicines
                
                stage_duration = int((time.time() - stage_start) * 1000)
                
                db_manager.log_processing_stage(
                    prescription_id, "validate", stage_duration, True
                )
                
                logger.info(f"Medicine validation completed in {stage_duration}ms")
                
            else:
                stage_duration = int((time.time() - stage_start) * 1000)
                
                db_manager.log_processing_stage(
                    prescription_id, "validate", stage_duration, True
                )
                
                logger.info("No medicines to validate")
                
        except Exception as e:
            stage_duration = int((time.time() - stage_start) * 1000)
            error_msg = f"Medicine validation failed: {str(e)}"
            
            db_manager.log_processing_stage(
                prescription_id, "validate", stage_duration, False, error_msg
            )
            
            result_data["extraction_failures"].append(error_msg)
            logger.error(error_msg)
        
        # Stage 5: Build final result
        total_processing_time = int((time.time() - start_time) * 1000)
        result_data["processing_time_ms"] = total_processing_time
        
        # Convert medicine dicts to MedicineItem objects
        medicine_items = []
        for med_dict in result_data["medicines"]:
            try:
                medicine_item = MedicineItem(**med_dict)
                medicine_items.append(medicine_item)
            except Exception as e:
                logger.warning(f"Failed to create MedicineItem: {e}")
                # Create a minimal medicine item
                medicine_item = MedicineItem(
                    name=med_dict.get("name", "Unknown"),
                    confidence=med_dict.get("confidence", 0.0),
                    fda_verified=False,
                    india_db_verified=False
                )
                medicine_items.append(medicine_item)
        
        result_data["medicines"] = medicine_items
        
        # Create ExtractionResult
        try:
            result = ExtractionResult(**result_data)
        except Exception as e:
            logger.error(f"Failed to create ExtractionResult: {e}")
            # Create minimal result
            result = ExtractionResult(
                id=prescription_id,
                medicines=[],
                ocr_raw=result_data["ocr_raw"],
                ocr_confidence=result_data["ocr_confidence"],
                extraction_failures=[f"Result creation failed: {str(e)}"],
                processing_time_ms=total_processing_time,
                model_used=self.model_name
            )
        
        # Stage 6: Save to database
        try:
            db_manager.save_prescription(result, image_hash)
            logger.info(f"Saved prescription {prescription_id} to database")
        except Exception as e:
            logger.error(f"Failed to save prescription to database: {e}")
            # Don't fail the pipeline for database errors
            result.extraction_failures.append(f"Database save failed: {str(e)}")
        
        logger.info(f"Pipeline completed for prescription {prescription_id} in {total_processing_time}ms")
        
        return result


# Global pipeline instance
pipeline = PrescriptionPipeline()


async def run_pipeline(image_bytes: bytes) -> ExtractionResult:
    """
    Main entry point for prescription processing pipeline.
    
    Args:
        image_bytes: Raw image data
        
    Returns:
        ExtractionResult with all extracted and validated data
    """
    return await pipeline.run_pipeline(image_bytes)