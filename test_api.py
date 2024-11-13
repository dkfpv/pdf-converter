import fitz
import os
from pathlib import Path

def test_pdf_processing(input_file, margin_mm=-24):
    try:
        print(f"Testing PDF processing with {input_file}")
        print(f"File exists: {os.path.exists(input_file)}")
        
        target_width = 4 * 72
        target_height = 6 * 72
        margin_points = margin_mm * 2.83465
        
        # Open source PDF
        src = fitz.open(input_file)
        print(f"Opened source PDF, pages: {len(src)}")
        
        # Create new PDF
        doc = fitz.open()
        
        for page_num in range(len(src)):
            page = src[page_num]
            width = page.rect.width
            start_x = (width / 2) - margin_points
            
            print(f"Processing page {page_num + 1}")
            print(f"Page width: {width}, start_x: {start_x}")
            
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
        output_file = "test_output.pdf"
        doc.save(output_file)
        doc.close()
        src.close()
        
        print(f"Successfully created {output_file}")
        print(f"Output file exists: {os.path.exists(output_file)}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    input_file = "/Users/danilakilin/Downloads/Etiquette (6).pdf"
    test_pdf_processing(input_file)