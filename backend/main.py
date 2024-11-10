from fastapi import FastAPI, UploadFile, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import fitz  # PyMuPDF
import os
from pathlib import Path
import tempfile
import uuid
import shutil
from datetime import datetime, timedelta
import asyncio
from typing import Optional
import logging
from pydantic import BaseModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PDF Label Converter API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create persistent storage directories
STORAGE_DIR = Path("storage")
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"
TEMP_DIR = STORAGE_DIR / "temp"

for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

class ConversionOptions(BaseModel):
    """Settings for PDF conversion"""
    margin_mm: float = -24
    width_inches: float = 4
    height_inches: float = 6
    dpi: int = 72
    quality: int = 100

class ConversionResponse(BaseModel):
    """Response model for conversion status"""
    job_id: str
    status: str
    message: str
    output_url: Optional[str] = None

# Store conversion jobs
conversion_jobs = {}

async def cleanup_old_files():
    """Clean up files older than 24 hours"""
    while True:
        try:
            current_time = datetime.now()
            for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
                for file in directory.glob("*"):
                    file_age = current_time - datetime.fromtimestamp(file.stat().st_mtime)
                    if file_age > timedelta(hours=24):
                        file.unlink()
                        logger.info(f"Cleaned up old file: {file}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        await asyncio.sleep(3600)  # Run every hour

@app.on_event("startup")
async def startup_event():
    """Start background tasks when the app starts"""
    asyncio.create_task(cleanup_old_files())

def process_pdf(input_path: Path, output_path: Path, options: ConversionOptions):
    """Process PDF with the given options"""
    try:
        # Calculate dimensions in points
        target_width = options.width_inches * options.dpi
        target_height = options.height_inches * options.dpi
        margin_points = options.margin_mm * 2.83465
        
        src = fitz.open(input_path)
        doc = fitz.open()
        
        for page_num in range(len(src)):
            page = src[page_num]
            width = page.rect.width
            start_x = (width / 2) - margin_points
            
            new_page = doc.new_page(
                width=target_width,
                height=target_height
            )
            
            src_rect = fitz.Rect(start_x, 0, width, page.rect.height)
            target_rect = fitz.Rect(0, 0, target_width, target_height)
            
            new_page.show_pdf_page(
                target_rect,
                src,
                page_num,
                clip=src_rect
            )
        
        # Save with specified quality
        doc.save(output_path, deflate_images=True, deflate=True)
        doc.close()
        src.close()
        return True
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise

@app.post("/api/convert")
async def convert_pdf(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    margin_mm: float = Query(-24, description="Margin in millimeters"),
    width_inches: float = Query(4, description="Target width in inches"),
    height_inches: float = Query(6, description="Target height in inches"),
    dpi: int = Query(72, description="Resolution in DPI"),
    quality: int = Query(100, description="Output quality (1-100)")
):
    try:
        # Validate input
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "File must be a PDF")
        
        # Generate unique IDs for files
        job_id = str(uuid.uuid4())
        input_path = UPLOAD_DIR / f"{job_id}_input.pdf"
        output_path = OUTPUT_DIR / f"{job_id}_output.pdf"
        
        # Save uploaded file
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create conversion options
        options = ConversionOptions(
            margin_mm=margin_mm,
            width_inches=width_inches,
            height_inches=height_inches,
            dpi=dpi,
            quality=quality
        )
        
        # Process PDF
        process_pdf(input_path, output_path, options)
        
        # Return processed file
        if not output_path.exists():
            raise HTTPException(500, "Failed to generate output file")
        
        return FileResponse(
            output_path,
            media_type='application/pdf',
            filename=f"{Path(file.filename).stem}_print.pdf",
            background=background_tasks.add_task(
                lambda: asyncio.sleep(3600) and output_path.unlink(missing_ok=True)
            )
        )
        
    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        raise HTTPException(500, f"Error processing PDF: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Check API health and storage status"""
    storage_info = {
        "uploads": len(list(UPLOAD_DIR.glob("*"))),
        "outputs": len(list(OUTPUT_DIR.glob("*"))),
        "temp": len(list(TEMP_DIR.glob("*")))
    }
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "storage": storage_info
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)