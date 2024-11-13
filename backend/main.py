from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import fitz  # PyMuPDF
import os
from pathlib import Path
import uuid
import logging
import sys
from datetime import datetime
import traceback

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="PDF Label Converter")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://label-pdf-crop.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage configuration with absolute paths
BASE_DIR = Path("/app")
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"

# Setup storage directories
def setup_storage():
    """Setup storage directories with proper permissions"""
    try:
        logger.info("Setting up storage directories")
        for directory in [STORAGE_DIR, UPLOAD_DIR, OUTPUT_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
            os.chmod(directory, 0o777)
            logger.info(f"Created and set permissions for directory: {directory}")
    except Exception as e:
        logger.error(f"Failed to setup storage directories: {e}")
        raise

setup_storage()

# Root endpoint
@app.get("/")
async def read_root():
    return {"status": "online", "message": "PDF Label Converter API"}

# Health check endpoint
@app.get("/health")
async def health_check():
    try:
        storage_info = {
            "uploads": len(list(UPLOAD_DIR.glob("*"))),
            "outputs": len(list(OUTPUT_DIR.glob("*"))),
        }
        return {
            "status": "healthy",
            "storage": storage_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(500, "Health check failed")

@app.post("/api/convert")
@app.post("//api/convert")  # Handle double slash case
async def convert_pdf(file: UploadFile, margin_mm: float = -24):
    input_path = None
    output_path = None

    try:
        logger.info(f"Starting conversion for file: {file.filename}")
        
        # Validate input file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "File must be a PDF")
        
        # Generate unique file paths
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_path = UPLOAD_DIR / f"{timestamp}_{uuid.uuid4()}_input.pdf"
        output_path = OUTPUT_DIR / f"{timestamp}_{uuid.uuid4()}_output.pdf"
        
        logger.info(f"Input path: {input_path}")
        logger.info(f"Output path: {output_path}")
        
        # Save uploaded file
        content = await file.read()
        logger.info(f"Read {len(content)} bytes from uploaded file")
        input_path.write_bytes(content)
        logger.info("File saved successfully")

        # Open and process PDF
        logger.info("Opening source PDF")
        try:
            src = fitz.open(str(input_path))
            logger.info(f"Source PDF opened, pages: {len(src)}")
        except Exception as e:
            logger.error(f"Failed to open input PDF: {e}")
            raise HTTPException(500, "Failed to open PDF file")

        doc = fitz.open()
        target_width = 4 * 72
        target_height = 6 * 72
        margin_points = margin_mm * 2.83465

        for page_num in range(len(src)):
            logger.info(f"Processing page {page_num + 1}/{len(src)}")
            page = src[page_num]
            width = page.rect.width
            start_x = (width / 2) - margin_points
            
            new_page = doc.new_page(width=target_width, height=target_height)
            src_rect = fitz.Rect(start_x, 0, width, page.rect.height)
            target_rect = fitz.Rect(0, 0, target_width, target_height)
            new_page.show_pdf_page(target_rect, src, page_num, clip=src_rect)
            
            logger.info(f"Page {page_num + 1} processed successfully")
        
        logger.info(f"Saving to output path: {output_path}")
        try:
            doc.save(str(output_path))
            logger.info("Output PDF saved successfully")
        except Exception as e:
            logger.error(f"Failed to save output PDF: {e}")
            raise HTTPException(500, "Failed to save processed PDF")
        finally:
            doc.close()
            src.close()
        
        # Clean up input file immediately
        if input_path.exists():
            input_path.unlink()
            logger.info(f"Cleaned up input file: {input_path}")
        
        # Verify output file existence
        if not output_path.exists():
            raise Exception(f"Output file was not created at {output_path}")
        
        # Set permissions for output file
        os.chmod(output_path, 0o644)
        logger.info("Set output file permissions")

        # Background cleanup function after response
        def cleanup_output():
            try:
                if output_path.exists():
                    output_path.unlink()
                    logger.info(f"Cleaned up output file: {output_path}")
            except Exception as e:
                logger.error(f"Error cleaning up output file: {e}")
        
        # Send response and schedule cleanup
        return FileResponse(
            str(output_path),
            media_type='application/pdf',
            filename=f"{Path(file.filename).stem}_print.pdf",
            background=cleanup_output  # Cleanup after file is sent
        )
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        logger.error(traceback.format_exc())
        
        # Cleanup in case of error
        try:
            if input_path and input_path.exists():
                input_path.unlink()
                logger.info(f"Cleaned up input file on error: {input_path}")
            if output_path and output_path.exists():
                output_path.unlink()
                logger.info(f"Cleaned up output file on error: {output_path}")
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup on failure: {cleanup_error}")
        
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)  # Adjusted port to 8080 as commonly used in containers
