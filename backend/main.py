from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import fitz  # PyMuPDF
import os
from pathlib import Path
import uuid
import logging
import sys
from datetime import datetime, timedelta
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
BASE_DIR = Path("/app")  # Railway uses /app as working directory
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"
TEMP_DIR = STORAGE_DIR / "temp"

# Log storage paths
logger.info("Storage paths:")
logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"STORAGE_DIR: {STORAGE_DIR}")
logger.info(f"UPLOAD_DIR: {UPLOAD_DIR}")
logger.info(f"OUTPUT_DIR: {OUTPUT_DIR}")

def setup_storage():
    """Setup storage directories with proper permissions"""
    try:
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info("Setting up storage directories")
        for directory in [STORAGE_DIR, UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
            os.chmod(directory, 0o777)
            logger.info(f"Created directory: {directory} with permissions 777")
            
            # Verify directory is writable
            test_file = directory / ".test"
            try:
                test_file.write_text("test")
                test_file.unlink()
                logger.info(f"Directory {directory} is writable")
            except Exception as e:
                logger.error(f"Directory {directory} is not writable: {e}")
                raise
                
    except Exception as e:
        logger.error(f"Failed to setup storage: {e}")
        logger.error(traceback.format_exc())
        raise

# Setup storage on startup
setup_storage()

def cleanup_old_files():
    """Remove files older than 5 minutes"""
    try:
        logger.info("Starting cleanup of old files")
        threshold = datetime.now() - timedelta(minutes=5)
        
        for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
            for file_path in directory.glob("*"):
                if datetime.fromtimestamp(file_path.stat().st_mtime) < threshold:
                    file_path.unlink()
                    logger.info(f"Cleaned up old file: {file_path}")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        logger.error(traceback.format_exc())

@app.get("/")
async def read_root():
    try:
        cleanup_old_files()
        return {"status": "online", "message": "PDF Label Converter API"}
    except Exception as e:
        logger.error(f"Error in root endpoint: {e}")
        raise HTTPException(500, "Internal server error")

@app.get("/health")
async def health_check():
    try:
        cleanup_old_files()
        storage_info = {
            "uploads": len(list(UPLOAD_DIR.glob("*"))),
            "outputs": len(list(OUTPUT_DIR.glob("*"))),
            "temp": len(list(TEMP_DIR.glob("*")))
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
        logger.info(f"Current working directory: {os.getcwd()}")
        
        # Validate input
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "File must be a PDF")
        
        # Generate file paths
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_path = UPLOAD_DIR / f"{timestamp}_{uuid.uuid4()}_input.pdf"
        output_path = OUTPUT_DIR / f"{timestamp}_{uuid.uuid4()}_output.pdf"
        
        logger.info(f"Input path: {input_path}")
        logger.info(f"Output path: {output_path}")
        
        # Save uploaded file
        try:
            content = await file.read()
            logger.info(f"Read {len(content)} bytes from uploaded file")
            input_path.write_bytes(content)
            logger.info("File saved successfully")
            
            if not input_path.exists():
                raise Exception(f"Input file was not created at {input_path}")
                
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(500, f"Error saving file: {str(e)}")
        
        try:
            # Convert PDF
            logger.info("Opening source PDF")
            src = fitz.open(str(input_path))
            logger.info(f"Source PDF opened, pages: {len(src)}")
            
            target_width = 4 * 72
            target_height = 6 * 72
            margin_points = margin_mm * 2.83465
            
            doc = fitz.open()
            logger.info("Created new PDF document")
            
            for page_num in range(len(src)):
                logger.info(f"Processing page {page_num + 1}/{len(src)}")
                page = src[page_num]
                width = page.rect.width
                start_x = (width / 2) - margin_points
                
                logger.info(f"Page dimensions - Width: {width}, Start X: {start_x}")
                
                new_page = doc.new_page(width=target_width, height=target_height)
                src_rect = fitz.Rect(start_x, 0, width, page.rect.height)
                target_rect = fitz.Rect(0, 0, target_width, target_height)
                new_page.show_pdf_page(target_rect, src, page_num, clip=src_rect)
                
                logger.info(f"Page {page_num + 1} processed")
            
            logger.info(f"Saving to: {output_path}")
            doc.save(str(output_path))
            doc.close()
            src.close()
            
            if not output_path.exists():
                raise Exception(f"Output file was not created at {output_path}")
            
            logger.info("PDF conversion completed successfully")
            
            # Set output file permissions
            os.chmod(output_path, 0o644)
            logger.info("Set output file permissions")
            
            return FileResponse(
                str(output_path),
                media_type='application/pdf',
                filename=f"{Path(file.filename).stem}_print.pdf",
                background=cleanup_old_files
            )
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(500, f"Error processing PDF: {str(e)}")
            
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(500, str(e))
        
    finally:
        # Cleanup
        try:
            if input_path and input_path.exists():
                input_path.unlink()
                logger.info(f"Cleaned up input file: {input_path}")
            if output_path and output_path.exists():
                output_path.unlink()
                logger.info(f"Cleaned up output file: {output_path}")
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
