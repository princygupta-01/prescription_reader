import json
import re
import logging
import time
import os
from groq import Groq
from typing import Dict, Any

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a medical data extractor specializing in Indian doctor prescriptions.

Extract structured data from the following OCR text of a handwritten prescription.

RULES:
- Return ONLY a valid JSON object. No explanation. No markdown. No prose before or after.
- If a field cannot be determined from the text, set it to null.
- For medicines, extract every medicine mentioned.
- Dosage examples: "1 tablet", "5ml", "1 cap", "2 drops"
- Frequency examples: "once daily", "twice daily", "TDS" (3x), "QID" (4x), "SOS" (as needed)
- Duration examples: "5 days", "1 week", "1 month", "continue"
- Set confidence between 0.0 and 1.0 based on how clearly you could read the field.
  Below 0.5 means you are guessing. Above 0.8 means the text was clear.
- Common Indian abbreviations: OD=once daily, BD=twice daily, TDS=3x daily,
  QID=4x daily, HS=at bedtime, AC=before meals, PC=after meals, SOS=as needed
- extraction_failures: list any fields you tried to extract but could not read clearly

OCR TEXT:
---
{ocr_text}
---

JSON SCHEMA (return exactly this structure):
{{
  "patient_name": string or null,
  "date": "YYYY-MM-DD" or null,
  "doctor_name": string or null,
  "doctor_reg_no": string or null,
  "medicines": [
    {{
      "name": string,
      "dosage": string or null,
      "frequency": string or null,
      "duration": string or null,
      "instructions": string or null,
      "confidence": float
    }}
  ],
  "general_instructions": string or null,
  "followup_date": "YYYY-MM-DD" or null,
  "extraction_failures": [string]
}}

JSON:"""


class LLMExtractor:
    """
    Groq LLM wrapper for extracting structured data from OCR text.
    """
    
    def __init__(self):
        """Initialize Groq client from environment variable"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        
        self.client = Groq(api_key=api_key)
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        
        logger.info(f"LLM Extractor initialized with model: {self.model}")
    
    def extract(self, ocr_text: str) -> Dict[str, Any]:
        """
        Extract structured data from OCR text using Groq LLM.
        
        Args:
            ocr_text: Raw text from OCR engine
            
        Returns:
            Dictionary with extracted fields and metadata
        """
        start_time = time.time()
        
        try:
            # Prepare prompt
            prompt = EXTRACTION_PROMPT.format(ocr_text=ocr_text)
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=1024,
                top_p=0.9
            )
            
            # Extract response text
            response_text = response.choices[0].message.content
            
            # Parse JSON from response
            extracted_data = self.robust_json_parse(response_text)
            
            # Add metadata
            extraction_time = time.time() - start_time
            extracted_data['_metadata'] = {
                'extraction_time_ms': int(extraction_time * 1000),
                'tokens_used': response.usage.total_tokens if response.usage else 0,
                'model_used': self.model
            }
            
            logger.info(f"LLM extraction completed in {extraction_time:.2f}s")
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return self._create_fallback_result(str(e))
    
    def robust_json_parse(self, text: str) -> Dict[str, Any]:
        """
        Robust JSON parsing with multiple fallback strategies.
        
        Tries in order:
        1. Direct json.loads(text.strip())
        2. Regex: find first { ... } block (greedy)
        3. Find ```json ... ``` block
        4. If all fail: return fallback structure
        
        Never raises - always returns a valid dict.
        """
        if not text:
            return self._create_fallback_result("Empty response from LLM")
        
        # Strategy 1: Direct parsing
        try:
            cleaned_text = text.strip()
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Find JSON block with regex (greedy match)
        try:
            json_pattern = r'\{.*\}'
            match = re.search(json_pattern, text, re.DOTALL)
            if match:
                json_str = match.group(0)
                return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Strategy 3: Find ```json code block
        try:
            json_block_pattern = r'```json\s*(.*?)\s*```'
            match = re.search(json_block_pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                json_str = match.group(1).strip()
                return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Strategy 4: Try to find any valid JSON-like structure
        try:
            # Look for lines that might contain JSON
            lines = text.split('\n')
            json_lines = []
            in_json = False
            brace_count = 0
            
            for line in lines:
                if '{' in line and not in_json:
                    in_json = True
                    json_lines.append(line)
                    brace_count += line.count('{') - line.count('}')
                elif in_json:
                    json_lines.append(line)
                    brace_count += line.count('{') - line.count('}')
                    if brace_count <= 0:
                        break
            
            if json_lines:
                json_str = '\n'.join(json_lines)
                return json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            pass
        
        # All strategies failed
        logger.warning(f"All JSON parsing strategies failed for text: {text[:200]}...")
        return self._create_fallback_result("LLM JSON parse failed")
    
    def _create_fallback_result(self, error_message: str) -> Dict[str, Any]:
        """Create a valid fallback result when parsing fails"""
        return {
            "patient_name": None,
            "date": None,
            "doctor_name": None,
            "doctor_reg_no": None,
            "medicines": [],
            "general_instructions": None,
            "followup_date": None,
            "extraction_failures": [error_message]
        }
    
    def validate_extraction_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean extraction result to ensure it matches expected schema.
        """
        try:
            # Ensure all required fields exist
            validated = {
                "patient_name": data.get("patient_name"),
                "date": data.get("date"),
                "doctor_name": data.get("doctor_name"),
                "doctor_reg_no": data.get("doctor_reg_no"),
                "medicines": [],
                "general_instructions": data.get("general_instructions"),
                "followup_date": data.get("followup_date"),
                "extraction_failures": data.get("extraction_failures", [])
            }
            
            # Validate medicines array
            medicines = data.get("medicines", [])
            if isinstance(medicines, list):
                for med in medicines:
                    if isinstance(med, dict) and med.get("name"):
                        validated_med = {
                            "name": str(med.get("name", "")),
                            "dosage": med.get("dosage"),
                            "frequency": med.get("frequency"),
                            "duration": med.get("duration"),
                            "instructions": med.get("instructions"),
                            "confidence": float(med.get("confidence", 0.5))
                        }
                        # Ensure confidence is in valid range
                        validated_med["confidence"] = max(0.0, min(1.0, validated_med["confidence"]))
                        validated["medicines"].append(validated_med)
            
            # Validate date formats
            for date_field in ["date", "followup_date"]:
                date_value = validated.get(date_field)
                if date_value and not self._is_valid_date_format(date_value):
                    validated[date_field] = None
                    if "Invalid date format" not in validated["extraction_failures"]:
                        validated["extraction_failures"].append(f"Invalid {date_field} format")
            
            return validated
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return self._create_fallback_result(f"Validation error: {str(e)}")
    
    def _is_valid_date_format(self, date_str: str) -> bool:
        """Check if date string matches YYYY-MM-DD format"""
        try:
            pattern = r'^\d{4}-\d{2}-\d{2}$'
            return bool(re.match(pattern, date_str))
        except:
            return False