import gradio as gr
import os
import asyncio
import tempfile
from PIL import Image
import io
import time
import json

from pipeline import run_pipeline
from models import ExtractionResult
from pdf_generator import generate_prescription_pdf
from database import init_db

# Ensure required environment variables
os.environ.setdefault("GROQ_MODEL", "llama-3.2-3b-instruct")
os.environ.setdefault("TROCR_MODEL", "microsoft/trocr-large-handwritten")

# Initialize database
init_db()

async def process_prescription(image):
    if image is None:
        return {"error": "Please upload an image."}, None
    
    # Convert PIL Image to bytes
    img_byte_arr = io.BytesIO()
    # Convert to RGB if it's RGBA
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    image.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    
    try:
        # Run the existing pipeline
        result = await run_pipeline(img_bytes)
        
        # Format the output for display
        output_data = {
            "Patient Info": {
                "Name": result.patient_name or "-",
                "Date": result.date or "-",
                "Doctor": result.doctor_name or "-",
                "Registration No": result.doctor_reg_no or "-"
            },
            "Instructions": {
                "General": result.general_instructions or "-",
                "Follow-up Date": result.followup_date or "-"
            }
        }
        
        # Format medicines
        medicines_list = []
        for med in result.medicines:
            med_dict = {
                "Name": med.name,
                "Dosage": med.dosage or "-",
                "Frequency": med.frequency or "-",
                "Duration": med.duration or "-",
                "Instructions": med.instructions or "-",
                "Confidence": f"{int(med.confidence * 100)}%",
                "Verified (FDA)": med.fda_verified,
                "Verified (India DB)": med.india_db_verified
            }
            medicines_list.append(med_dict)
            
        output_data["Medicines"] = medicines_list
        if result.extraction_failures:
            output_data["Extraction Failures"] = result.extraction_failures
            
        output_data["OCR Quality"] = f"{int(result.ocr_confidence * 100)}%"
        output_data["Processing Time"] = f"{result.processing_time_ms}ms"
        
        # Generate PDF
        try:
            pdf_bytes = generate_prescription_pdf(result)
            tmp_dir = tempfile.gettempdir()
            pdf_path = os.path.join(tmp_dir, f"prescription_{result.id}.pdf")
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
        except Exception as e:
            print(f"PDF generation error: {e}")
            pdf_path = None
            
        return output_data, pdf_path
        
    except Exception as e:
        return {"error": f"Error processing prescription: {str(e)}"}, None

def process_wrapper(image):
    # Run async function in sync context for Gradio
    return asyncio.run(process_prescription(image))

# Create Gradio interface
with gr.Blocks(title="PrescriptionReader - AI Digitization", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # PrescriptionReader
        ### Handwritten Indian prescription → structured digital record in seconds.
        Upload a photo of a handwritten doctor's prescription. Our AI pipeline will read it using **TrOCR**, structure the data using **Llama 3.2**, and validate the medicines instantly.
        """
    )
    
    with gr.Row():
        with gr.Column(scale=1):
            input_image = gr.Image(type="pil", label="Upload Prescription Photo")
            submit_btn = gr.Button("Analyze Prescription", variant="primary")
            
        with gr.Column(scale=1):
            output_json = gr.JSON(label="Extracted Structured Data")
            output_pdf = gr.File(label="Download PDF Record")
            
    submit_btn.click(
        fn=process_wrapper,
        inputs=input_image,
        outputs=[output_json, output_pdf]
    )
    
    gr.Markdown("""
    ---
    ### How it works
    1. **Preprocessing**: Deskewing, denoising, contrast enhancement
    2. **OCR**: Microsoft TrOCR-large (1.3B) reads the handwriting
    3. **Extraction**: Llama 3.2 3B structures the text into JSON fields
    4. **Validation**: Parallel OpenFDA and Indian drug database lookup
    """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
