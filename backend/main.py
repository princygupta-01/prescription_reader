from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import os
import uuid
import time
from typing import Dict, Any
import io

# Load .env before any local imports that read env vars
from dotenv import load_dotenv
load_dotenv()

from models import UploadResponse, PollResponse, ExtractionResult
from pipeline import run_pipeline
from database import init_db, get_prescription, get_stats
from pdf_generator import generate_prescription_pdf
from ocr import ocr_engine
from extractor import LLMExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PrescriptionReader API",
    description="AI-powered prescription digitization service",
    version="1.0.0"
)

# CORS middleware - allow all origins for hackathon
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for tracking processing tasks
processing_tasks: Dict[str, Dict[str, Any]] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        logger.info("Starting PrescriptionReader API...")
        
        # Initialize database
        init_db()
        logger.info("Database initialized")
        
        # Warm up TrOCR model (this loads the model)
        logger.info("Loading TrOCR model...")
        from PIL import Image
        test_image = Image.new('RGB', (224, 224), color='white')
        ocr_engine.extract_text(test_image)
        logger.info("TrOCR model loaded and warmed up")
        
        # Test Groq connection
        try:
            extractor = LLMExtractor()
            logger.info("Groq LLM connection verified")
        except Exception as e:
            logger.warning(f"Groq connection failed: {e}")
        
        logger.info("PrescriptionReader API started successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


@app.post("/api/upload", response_model=UploadResponse)
async def upload_prescription(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload prescription image for processing.
    
    - Accept multipart/form-data with "file" field (image)
    - Validate: image only (jpg, png, webp, heic), max 10MB
    - Run pipeline in background task
    - Return: {"task_id": uuid, "status": "processing"}
    """
    
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Validate file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum size: 10MB"
            )
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task tracking
        processing_tasks[task_id] = {
            "status": "processing",
            "stage": "preprocessing",
            "progress": 0.0,
            "start_time": time.time(),
            "result": None,
            "error": None
        }
        
        # Start background processing
        background_tasks.add_task(process_prescription_background, task_id, file_content)
        
        logger.info(f"Started processing task {task_id} for file {file.filename}")
        
        return UploadResponse(task_id=task_id, status="processing")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def process_prescription_background(task_id: str, image_bytes: bytes):
    """Background task to process prescription"""
    try:
        logger.info(f"Starting background processing for task {task_id}")
        
        # Update progress stages
        stages = [
            ("preprocessing", 0.1),
            ("ocr", 0.4),
            ("extraction", 0.7),
            ("validation", 0.9)
        ]
        
        # Process with progress updates
        for stage, progress in stages:
            processing_tasks[task_id]["stage"] = stage
            processing_tasks[task_id]["progress"] = progress
            
            # Small delay to show progress (remove in production)
            await asyncio.sleep(0.1)
        
        # Run the actual pipeline
        result = await run_pipeline(image_bytes)
        
        # Update task with result
        processing_tasks[task_id].update({
            "status": "done",
            "stage": "completed",
            "progress": 1.0,
            "result": result,
            "error": None
        })
        
        logger.info(f"Completed processing task {task_id}")
        
    except Exception as e:
        logger.error(f"Background processing failed for task {task_id}: {e}")
        
        processing_tasks[task_id].update({
            "status": "failed",
            "stage": "error",
            "progress": 0.0,
            "result": None,
            "error": str(e)
        })


@app.get("/api/result/{task_id}", response_model=PollResponse)
async def get_result(task_id: str):
    """
    Poll endpoint for processing status.
    
    - If still processing: {"status": "processing", "stage": "ocr", "progress": 0.4}
    - If done: {"status": "done", "result": ExtractionResult}
    - If failed: {"status": "failed", "error": "...", "ocr_raw": "..."}
    """
    
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = processing_tasks[task_id]
    
    response_data = {
        "status": task["status"],
        "stage": task.get("stage"),
        "progress": task.get("progress")
    }
    
    if task["status"] == "done":
        response_data["result"] = task["result"]
    elif task["status"] == "failed":
        response_data["error"] = task["error"]
        # Include OCR raw text if available for debugging
        if task.get("result") and hasattr(task["result"], "ocr_raw"):
            response_data["ocr_raw"] = task["result"].ocr_raw
    
    return PollResponse(**response_data)


@app.get("/api/export/{prescription_id}/pdf")
async def export_pdf(prescription_id: str):
    """
    Generate and stream PDF for a prescription.
    
    - Generate and stream PDF
    - Response headers: Content-Type: application/pdf, Content-Disposition: attachment
    """
    
    try:
        # Get prescription from database
        result = get_prescription(prescription_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Prescription not found")
        
        # Generate PDF
        pdf_bytes = generate_prescription_pdf(result)
        
        if not pdf_bytes:
            raise HTTPException(status_code=500, detail="PDF generation failed")
        
        # Create streaming response
        pdf_stream = io.BytesIO(pdf_bytes)
        
        headers = {
            "Content-Disposition": f"attachment; filename=prescription_{prescription_id}.pdf"
        }
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF export failed for {prescription_id}: {e}")
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")


@app.get("/api/stats")
async def get_processing_stats():
    """
    Return processing statistics for README/demo purposes.
    
    Returns:
    - {"total_processed": int, "avg_medicine_accuracy": float, "model_used": str}
    """
    
    try:
        stats = get_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {
            "total_processed": 0,
            "avg_medicine_accuracy": 0.0,
            "model_used": "TrOCR-large + Llama-3.2-3B",
            "error": str(e)
        }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
    - {"status": "ok", "models_loaded": bool, "groq_connected": bool}
    """
    
    models_loaded = False
    groq_connected = False
    
    try:
        # Check if TrOCR is loaded
        if hasattr(ocr_engine, 'model') and ocr_engine.model is not None:
            models_loaded = True
    except:
        pass
    
    try:
        # Check Groq connection
        extractor = LLMExtractor()
        groq_connected = True
    except:
        pass
    
    return {
        "status": "ok",
        "models_loaded": models_loaded,
        "groq_connected": groq_connected,
        "active_tasks": len(processing_tasks)
    }


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "PrescriptionReader API",
        "version": "1.0.0",
        "description": "AI-powered prescription digitization service",
        "endpoints": {
            "upload": "/api/upload",
            "result": "/api/result/{task_id}",
            "export": "/api/export/{prescription_id}/pdf",
            "stats": "/api/stats",
            "health": "/health"
        }
    }


# Cleanup old tasks periodically (prevent memory leaks)
@app.on_event("startup")
async def start_cleanup_task():
    """Start periodic cleanup of old processing tasks"""
    
    async def cleanup_old_tasks():
        while True:
            try:
                current_time = time.time()
                old_tasks = []
                
                for task_id, task in processing_tasks.items():
                    # Remove tasks older than 1 hour
                    if current_time - task.get("start_time", 0) > 3600:
                        old_tasks.append(task_id)
                
                for task_id in old_tasks:
                    del processing_tasks[task_id]
                
                if old_tasks:
                    logger.info(f"Cleaned up {len(old_tasks)} old tasks")
                
            except Exception as e:
                logger.error(f"Task cleanup failed: {e}")
            
            # Run cleanup every 10 minutes
            await asyncio.sleep(600)
    
    # Start cleanup task
    asyncio.create_task(cleanup_old_tasks())


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Set to True for development
        log_level="info"
    )