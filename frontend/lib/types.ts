// TypeScript types that exactly mirror the backend Pydantic models

export interface MedicineItem {
  name: string;
  dosage: string | null;
  frequency: string | null;
  duration: string | null;
  instructions: string | null;
  confidence: number; // 0.0 to 1.0
  fda_verified: boolean;
  india_db_verified: boolean;
}

export interface ExtractionResult {
  id: string; // uuid
  patient_name: string | null;
  date: string | null; // YYYY-MM-DD
  doctor_name: string | null;
  doctor_reg_no: string | null;
  medicines: MedicineItem[];
  general_instructions: string | null;
  followup_date: string | null; // YYYY-MM-DD
  ocr_raw: string;
  ocr_confidence: number; // average character confidence from TrOCR
  extraction_failures: string[]; // fields that could not be extracted
  processing_time_ms: number;
  model_used: string;
}

export interface UploadResponse {
  task_id: string;
  status: string; // "processing" | "done" | "failed"
}

export interface PollResponse {
  status: 'processing' | 'done' | 'failed';
  stage?: string;
  progress?: number;
  result?: ExtractionResult;
  error?: string;
  ocr_raw?: string;
}

export interface Stats {
  total_processed: number;
  success_rate: number;
  avg_processing_time_ms: number;
  avg_medicine_accuracy: number;
  total_medicines_processed: number;
  high_confidence_medicines: number;
  model_used: string;
}

export interface ProcessingStage {
  name: string;
  label: string;
  estimatedTime: number; // in seconds
}

export const PROCESSING_STAGES: ProcessingStage[] = [
  { name: 'preprocessing', label: 'Enhancing image', estimatedTime: 1 },
  { name: 'ocr', label: 'Reading handwriting', estimatedTime: 8 },
  { name: 'extraction', label: 'Extracting data', estimatedTime: 2 },
  { name: 'validation', label: 'Validating medicines', estimatedTime: 1 }
];