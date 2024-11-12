from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import fitz  # PyMuPDF
import os
from pathlib import Path
import tempfile
import uuid
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PDF Label Converter")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  
        "https://label-pdf-crop.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PythonAnywhere specific paths
USERNAME = "your_pythonanywhere_username"  # Replace with your username
BASE_DIR = Path(f"/home/{USERNAME}/pdf_converter")
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"
TEMP_DIR = STORAGE_DIR / "temp"

# Create storage directories with full permissions
for directory in [STORAGE_DIR, UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
    # Make directory writable
    os.chmod(directory, 0o777)

def cleanup_old_files():
    """Remove files older than 5 minutes"""
    try:
        threshold = datetime.now() - timedelta(minutes=5)
        
        for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
            for file_path in directory.glob("*"):
                if datetime.fromtimestamp(file_path.stat().st_mtime) < threshold:
                    try:
                        file_path.unlink()
                        logger.info(f"Cleaned up old file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

@app.get("/")
async def read_root():
    cleanup_old_files()  # Cleanup on each request
    return {"status": "online", "message": "PDF Label Converter API"}

@app.get("/health")
async def health_check():
    cleanup_old_files()
    return {
        "status": "healthy",
        "storage": {
            "uploads": len(list(UPLOAD_DIR.glob("*"))),
            "outputs": len(list(OUTPUT_DIR.glob("*"))),
            "temp": len(list(TEMP_DIR.glob("*")))
        }
    }

@app.post("/api/convert")
async def convert_pdf(
    file: UploadFile,
    margin_mm: float = -24
):
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "File must be a PDF")
        
        # Generate unique file paths with timestamps
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_path = UPLOAD_DIR / f"{timestamp}_{uuid.uuid4()}_input.pdf"
        output_path = OUTPUT_DIR / f"{timestamp}_{uuid.uuid4()}_output.pdf"
        
        # Save uploaded file
        try:
            with open(input_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
        except Exception as e:
            logger.error(f"Error saving uploaded file: {e}")
            raise HTTPException(500, "Error saving uploaded file")
        
        try:
            # Convert PDF
            target_width = 4 * 72  # 288 points (4 inches)
            target_height = 6 * 72  # 432 points (6 inches)
            margin_points = margin_mm * 2.83465
            
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
            
            # Save result
            doc.save(output_path)
            doc.close()
            src.close()
            
            # Ensure file exists and is readable
            if not output_path.exists():
                raise HTTPException(500, "Failed to generate output file")
            
            # Set file permissions
            os.chmod(output_path, 0o644)
            
            return FileResponse(
                output_path,
                media_type='application/pdf',
                filename=f"{Path(file.filename).stem}_print.pdf",
                background=cleanup_old_files  # Clean up after sending
            )
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise HTTPException(500, f"Error processing PDF: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error handling upload: {e}")
        raise HTTPException(500, f"Error handling upload: {str(e)}")

# Only used for local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)