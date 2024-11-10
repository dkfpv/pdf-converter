from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import fitz  # PyMuPDF
import os
from pathlib import Path
import tempfile
import uuid
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PDF Label Converter")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create storage directories
STORAGE_DIR = Path("storage")
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"
TEMP_DIR = STORAGE_DIR / "temp"

for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

@app.get("/")
async def read_root():
    return {"status": "online", "message": "PDF Label Converter API"}

@app.get("/health")
async def health_check():
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
        
        # Generate unique file paths
        input_path = UPLOAD_DIR / f"{uuid.uuid4()}_input.pdf"
        output_path = OUTPUT_DIR / f"{uuid.uuid4()}_output.pdf"
        
        # Save uploaded file
        with open(input_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
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
            
            # Return the processed file
            return FileResponse(
                output_path,
                media_type='application/pdf',
                filename=f"{Path(file.filename).stem}_print.pdf"
            )
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise HTTPException(500, f"Error processing PDF: {str(e)}")
            
        finally:
            # Cleanup
            if input_path.exists():
                input_path.unlink()
            if output_path.exists():
                output_path.unlink()
            
    except Exception as e:
        logger.error(f"Error handling upload: {e}")
        raise HTTPException(500, f"Error handling upload: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)