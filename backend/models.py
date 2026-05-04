from pydantic import BaseModel
from typing import Optional, List


class MedicineItem(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    confidence: float  # 0.0 to 1.0
    fda_verified: bool = False
    india_db_verified: bool = False


class ExtractionResult(BaseModel):
    id: str  # uuid
    patient_name: Optional[str] = None
    date: Optional[str] = None  # YYYY-MM-DD
    doctor_name: Optional[str] = None
    doctor_reg_no: Optional[str] = None
    medicines: List[MedicineItem]
    general_instructions: Optional[str] = None
    followup_date: Optional[str] = None
    ocr_raw: str
    ocr_confidence: float  # average character confidence from TrOCR
    extraction_failures: List[str]  # fields that could not be extracted
    processing_time_ms: int
    model_used: str


class UploadResponse(BaseModel):
    task_id: str
    status: str  # "processing" | "done" | "failed"


class ExportRequest(BaseModel):
    prescription_id: str


class PollResponse(BaseModel):
    status: str  # "processing" | "done" | "failed"
    stage: Optional[str] = None
    progress: Optional[float] = None
    result: Optional[ExtractionResult] = None
    error: Optional[str] = None


class Stats(BaseModel):
    total_processed: int
    avg_medicine_accuracy: float
    model_used: str