from sqlalchemy import create_engine, Column, String, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
import json
import logging
import os
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from models import ExtractionResult

logger = logging.getLogger(__name__)

Base = declarative_base()


class Prescription(Base):
    """Table: prescriptions"""
    __tablename__ = "prescriptions"
    
    id = Column(String, primary_key=True)  # uuid
    created_at = Column(DateTime, default=func.now())
    image_hash = Column(String, nullable=False)  # sha256 of original image
    ocr_raw = Column(Text, nullable=False)  # raw OCR text
    result_json = Column(Text, nullable=False)  # ExtractionResult as JSON
    processing_time_ms = Column(Integer, nullable=False)
    status = Column(String, nullable=False)  # "done" | "failed"
    error_message = Column(Text, nullable=True)
    
    # Relationship to processing logs
    processing_logs = relationship("ProcessingLog", back_populates="prescription")


class ProcessingLog(Base):
    """Table: processing_log"""
    __tablename__ = "processing_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    prescription_id = Column(String, ForeignKey("prescriptions.id"), nullable=False)
    stage = Column(String, nullable=False)  # preprocess/ocr/extract/validate
    duration_ms = Column(Integer, nullable=False)
    success = Column(Boolean, nullable=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationship to prescription
    prescription = relationship("Prescription", back_populates="processing_logs")


class DatabaseManager:
    """Database manager for prescription processing"""
    
    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            database_url = os.getenv("DATABASE_URL", "sqlite:///./prescriptions.db")
        
        self.engine = create_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        logger.info(f"Database initialized: {database_url}")
    
    def init_db(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()
    
    def save_prescription(self, result: ExtractionResult, image_hash: str) -> str:
        """
        Save prescription result to database.
        
        Args:
            result: ExtractionResult object
            image_hash: SHA256 hash of original image
            
        Returns:
            Prescription ID
        """
        session = self.get_session()
        try:
            # Convert result to JSON
            result_dict = result.dict()
            result_json = json.dumps(result_dict, default=str)
            
            # Create prescription record
            prescription = Prescription(
                id=result.id,
                image_hash=image_hash,
                ocr_raw=result.ocr_raw,
                result_json=result_json,
                processing_time_ms=result.processing_time_ms,
                status="done" if not result.extraction_failures else "done",  # Always "done" if we got a result
                error_message=None
            )
            
            session.add(prescription)
            session.commit()
            
            logger.info(f"Saved prescription {result.id} to database")
            return result.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save prescription: {e}")
            raise
        finally:
            session.close()
    
    def save_failed_prescription(self, prescription_id: str, image_hash: str, 
                               error_message: str, processing_time_ms: int) -> str:
        """
        Save a failed prescription processing attempt.
        
        Args:
            prescription_id: UUID for the prescription
            image_hash: SHA256 hash of original image
            error_message: Error description
            processing_time_ms: Time spent processing before failure
            
        Returns:
            Prescription ID
        """
        session = self.get_session()
        try:
            prescription = Prescription(
                id=prescription_id,
                image_hash=image_hash,
                ocr_raw="",
                result_json="{}",
                processing_time_ms=processing_time_ms,
                status="failed",
                error_message=error_message
            )
            
            session.add(prescription)
            session.commit()
            
            logger.info(f"Saved failed prescription {prescription_id} to database")
            return prescription_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save failed prescription: {e}")
            raise
        finally:
            session.close()
    
    def get_prescription(self, prescription_id: str) -> Optional[ExtractionResult]:
        """
        Retrieve prescription by ID.
        
        Args:
            prescription_id: UUID of the prescription
            
        Returns:
            ExtractionResult object or None if not found
        """
        session = self.get_session()
        try:
            prescription = session.query(Prescription).filter(
                Prescription.id == prescription_id
            ).first()
            
            if not prescription:
                return None
            
            if prescription.status == "failed":
                return None
            
            # Parse JSON back to ExtractionResult
            result_dict = json.loads(prescription.result_json)
            return ExtractionResult(**result_dict)
            
        except Exception as e:
            logger.error(f"Failed to retrieve prescription {prescription_id}: {e}")
            return None
        finally:
            session.close()
    
    def log_processing_stage(self, prescription_id: str, stage: str, 
                           duration_ms: int, success: bool, error: Optional[str] = None):
        """
        Log a processing stage for a prescription.
        
        Args:
            prescription_id: UUID of the prescription
            stage: Stage name (preprocess/ocr/extract/validate)
            duration_ms: Time taken for this stage
            success: Whether the stage succeeded
            error: Error message if failed
        """
        session = self.get_session()
        try:
            log_entry = ProcessingLog(
                prescription_id=prescription_id,
                stage=stage,
                duration_ms=duration_ms,
                success=success,
                error=error
            )
            
            session.add(log_entry)
            session.commit()
            
            logger.debug(f"Logged {stage} stage for prescription {prescription_id}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log processing stage: {e}")
        finally:
            session.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with statistics
        """
        session = self.get_session()
        try:
            # Total processed prescriptions
            total_processed = session.query(Prescription).count()
            
            # Success rate
            successful = session.query(Prescription).filter(
                Prescription.status == "done"
            ).count()
            
            # Average processing time
            avg_processing_time = session.query(func.avg(Prescription.processing_time_ms)).scalar() or 0
            
            # Medicine accuracy (approximate based on successful extractions)
            successful_prescriptions = session.query(Prescription).filter(
                Prescription.status == "done"
            ).all()
            
            total_medicines = 0
            high_confidence_medicines = 0
            
            for prescription in successful_prescriptions:
                try:
                    result_dict = json.loads(prescription.result_json)
                    medicines = result_dict.get('medicines', [])
                    total_medicines += len(medicines)
                    high_confidence_medicines += sum(
                        1 for med in medicines if med.get('confidence', 0) >= 0.8
                    )
                except:
                    continue
            
            avg_medicine_accuracy = (
                high_confidence_medicines / total_medicines 
                if total_medicines > 0 else 0.0
            )
            
            # Stage-wise performance
            stage_stats = {}
            stages = ['preprocess', 'ocr', 'extract', 'validate']
            
            for stage in stages:
                stage_logs = session.query(ProcessingLog).filter(
                    ProcessingLog.stage == stage
                ).all()
                
                if stage_logs:
                    success_rate = sum(1 for log in stage_logs if log.success) / len(stage_logs)
                    avg_duration = sum(log.duration_ms for log in stage_logs) / len(stage_logs)
                    
                    stage_stats[stage] = {
                        'success_rate': success_rate,
                        'avg_duration_ms': avg_duration,
                        'total_runs': len(stage_logs)
                    }
            
            return {
                'total_processed': total_processed,
                'success_rate': successful / total_processed if total_processed > 0 else 0.0,
                'avg_processing_time_ms': int(avg_processing_time),
                'avg_medicine_accuracy': avg_medicine_accuracy,
                'total_medicines_processed': total_medicines,
                'high_confidence_medicines': high_confidence_medicines,
                'stage_performance': stage_stats,
                'model_used': 'TrOCR-large + Llama-3.2-3B'
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                'total_processed': 0,
                'success_rate': 0.0,
                'avg_processing_time_ms': 0,
                'avg_medicine_accuracy': 0.0,
                'model_used': 'TrOCR-large + Llama-3.2-3B'
            }
        finally:
            session.close()
    
    def cleanup_old_records(self, days: int = 30):
        """
        Clean up old prescription records (optional maintenance function).
        
        Args:
            days: Number of days to keep records
        """
        session = self.get_session()
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Delete old processing logs first (foreign key constraint)
            old_logs = session.query(ProcessingLog).join(Prescription).filter(
                Prescription.created_at < cutoff_date
            ).delete(synchronize_session=False)
            
            # Delete old prescriptions
            old_prescriptions = session.query(Prescription).filter(
                Prescription.created_at < cutoff_date
            ).delete(synchronize_session=False)
            
            session.commit()
            
            logger.info(f"Cleaned up {old_prescriptions} old prescriptions and {old_logs} logs")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to cleanup old records: {e}")
        finally:
            session.close()


def calculate_image_hash(image_bytes: bytes) -> str:
    """Calculate SHA256 hash of image bytes"""
    return hashlib.sha256(image_bytes).hexdigest()


# Global database manager instance
db_manager = DatabaseManager()


def init_db():
    """Initialize database tables"""
    db_manager.init_db()


def save_prescription(result: ExtractionResult, image_hash: str) -> str:
    """Save prescription result to database"""
    return db_manager.save_prescription(result, image_hash)


def get_prescription(prescription_id: str) -> Optional[ExtractionResult]:
    """Get prescription by ID"""
    return db_manager.get_prescription(prescription_id)


def get_stats() -> Dict[str, Any]:
    """Get processing statistics"""
    return db_manager.get_stats()