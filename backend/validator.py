import asyncio
import aiohttp
import logging
import time
from typing import Dict, List
from urllib.parse import quote
from indian_drugs import INDIAN_DRUG_NAMES

logger = logging.getLogger(__name__)

# Cache for validation results (process lifetime)
_validation_cache = {}


async def validate_medicine_name(name: str) -> Dict[str, any]:
    """
    Check medicine name against two sources in parallel:
    
    1. OpenFDA API:
       GET https://api.fda.gov/drug/label.json?search=openfda.brand_name:"{name}"&limit=1
       If results > 0: fda_verified = True
       Timeout: 3 seconds. On timeout/error: fda_verified = False (don't fail the pipeline)
    
    2. INDIAN_DRUG_NAMES set from indian_drugs.py:
       Check if name.lower() or any word in name.lower() matches the set
       india_db_verified = True/False
    
    Returns: {"fda_verified": bool, "india_db_verified": bool, "normalized_name": str}
    
    Cache results in a simple dict for the process lifetime.
    """
    if not name or not name.strip():
        return {
            "fda_verified": False,
            "india_db_verified": False,
            "normalized_name": ""
        }
    
    # Normalize name for caching
    normalized_name = name.strip().lower()
    
    # Check cache first
    if normalized_name in _validation_cache:
        logger.debug(f"Cache hit for medicine: {name}")
        return _validation_cache[normalized_name]
    
    start_time = time.time()
    
    # Run both validations in parallel
    fda_task = asyncio.create_task(_validate_fda(name))
    india_task = asyncio.create_task(_validate_indian_db(name))
    
    try:
        fda_verified, india_db_verified = await asyncio.gather(
            fda_task, india_task, return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(fda_verified, Exception):
            logger.warning(f"FDA validation failed for {name}: {fda_verified}")
            fda_verified = False
        
        if isinstance(india_db_verified, Exception):
            logger.warning(f"Indian DB validation failed for {name}: {india_db_verified}")
            india_db_verified = False
        
        result = {
            "fda_verified": bool(fda_verified),
            "india_db_verified": bool(india_db_verified),
            "normalized_name": normalized_name
        }
        
        # Cache the result
        _validation_cache[normalized_name] = result
        
        validation_time = time.time() - start_time
        logger.info(f"Validated '{name}' in {validation_time:.2f}s - FDA: {fda_verified}, India: {india_db_verified}")
        
        return result
        
    except Exception as e:
        logger.error(f"Medicine validation failed for {name}: {e}")
        # Return safe fallback
        result = {
            "fda_verified": False,
            "india_db_verified": False,
            "normalized_name": normalized_name
        }
        _validation_cache[normalized_name] = result
        return result


async def _validate_fda(name: str) -> bool:
    """
    Validate medicine name against OpenFDA API.
    Returns True if found, False otherwise (including on errors).
    """
    try:
        # Prepare search query
        encoded_name = quote(name)
        url = f"https://api.fda.gov/drug/label.json?search=openfda.brand_name:\"{encoded_name}\"&limit=1"
        
        timeout = aiohttp.ClientTimeout(total=3.0)  # 3 second timeout
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # Check if any results found
                    results = data.get('results', [])
                    return len(results) > 0
                else:
                    logger.debug(f"FDA API returned status {response.status} for {name}")
                    return False
                    
    except asyncio.TimeoutError:
        logger.debug(f"FDA API timeout for {name}")
        return False
    except Exception as e:
        logger.debug(f"FDA API error for {name}: {e}")
        return False


async def _validate_indian_db(name: str) -> bool:
    """
    Validate medicine name against Indian drug database.
    Check if name.lower() or any word in name.lower() matches the set.
    """
    try:
        normalized_name = name.lower().strip()
        
        # Direct match
        if normalized_name in INDIAN_DRUG_NAMES:
            return True
        
        # Check individual words
        words = normalized_name.split()
        for word in words:
            # Remove common non-drug words
            if word in ['tablet', 'capsule', 'syrup', 'injection', 'mg', 'ml', 'gm']:
                continue
            
            if word in INDIAN_DRUG_NAMES:
                return True
        
        # Check partial matches for compound names
        for drug_name in INDIAN_DRUG_NAMES:
            if drug_name in normalized_name or normalized_name in drug_name:
                # Avoid false positives with very short matches
                if len(drug_name) >= 4 and len(normalized_name) >= 4:
                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"Indian DB validation error for {name}: {e}")
        return False


async def validate_all_medicines(medicines: List[Dict]) -> List[Dict]:
    """
    Run validation for all medicines concurrently using asyncio.gather.
    
    Args:
        medicines: List of medicine dictionaries from LLM extraction
        
    Returns:
        List of medicine dictionaries with fda_verified and india_db_verified fields added
    """
    if not medicines:
        return []
    
    start_time = time.time()
    
    try:
        # Create validation tasks for all medicines
        validation_tasks = []
        for medicine in medicines:
            medicine_name = medicine.get('name', '')
            if medicine_name:
                task = validate_medicine_name(medicine_name)
                validation_tasks.append(task)
            else:
                # Create a dummy task for medicines without names
                async def dummy_validation():
                    return {"fda_verified": False, "india_db_verified": False, "normalized_name": ""}
                validation_tasks.append(dummy_validation())
        
        # Run all validations concurrently
        validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # Merge validation results with medicine data
        validated_medicines = []
        for i, medicine in enumerate(medicines):
            validated_medicine = medicine.copy()
            
            if i < len(validation_results):
                validation_result = validation_results[i]
                
                if isinstance(validation_result, Exception):
                    logger.warning(f"Validation failed for medicine {i}: {validation_result}")
                    validated_medicine['fda_verified'] = False
                    validated_medicine['india_db_verified'] = False
                else:
                    validated_medicine['fda_verified'] = validation_result.get('fda_verified', False)
                    validated_medicine['india_db_verified'] = validation_result.get('india_db_verified', False)
            else:
                validated_medicine['fda_verified'] = False
                validated_medicine['india_db_verified'] = False
            
            validated_medicines.append(validated_medicine)
        
        total_time = time.time() - start_time
        verified_count = sum(1 for m in validated_medicines 
                           if m.get('fda_verified') or m.get('india_db_verified'))
        
        logger.info(f"Validated {len(medicines)} medicines in {total_time:.2f}s - "
                   f"{verified_count} verified")
        
        return validated_medicines
        
    except Exception as e:
        logger.error(f"Batch medicine validation failed: {e}")
        # Return original medicines with validation fields set to False
        fallback_medicines = []
        for medicine in medicines:
            fallback_medicine = medicine.copy()
            fallback_medicine['fda_verified'] = False
            fallback_medicine['india_db_verified'] = False
            fallback_medicines.append(fallback_medicine)
        return fallback_medicines


def get_validation_stats() -> Dict[str, any]:
    """
    Get statistics about validation cache and performance.
    """
    return {
        "cached_medicines": len(_validation_cache),
        "fda_verified_count": sum(1 for result in _validation_cache.values() 
                                 if result.get('fda_verified')),
        "india_verified_count": sum(1 for result in _validation_cache.values() 
                                   if result.get('india_db_verified')),
        "total_indian_drugs": len(INDIAN_DRUG_NAMES)
    }


def clear_validation_cache():
    """Clear the validation cache (useful for testing)"""
    global _validation_cache
    _validation_cache = {}
    logger.info("Validation cache cleared")